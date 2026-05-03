//! ECS-style world: nutrients, chemistry, hyphae, signals, memory, organisms.

use rand::Rng;
use serde::{Deserialize, Serialize};

use crate::chemistry::{self, ChemistryGrid};
use crate::config::{SimulationConfig, DT};
use crate::hypha::{anastomosis, HyphaTip};
use crate::memory::GrowthMemory;
use crate::nutrients::NutrientFields;
use crate::organisms::{
    bacteria, cells, fungi, mildew, mold, virus, OrganismClass, OrganismInstance,
};
use crate::rng::{rng_from_seed, SimRng};
use crate::signal::SignalField;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct StateSnapshot {
    pub frame: u64,
    pub paused: bool,
    pub seed_hex: String,
    pub tip_count: usize,
    pub organism_count: usize,
    pub mean_sugar: f32,
    pub mean_nitrogen: f32,
    pub chemistry_means: [f32; chemistry::N_COMPOUNDS],
    pub tips: Vec<HyphaTip>,
    pub organisms: Vec<OrganismInstance>,
    pub events_tail: Vec<String>,
}

pub struct World {
    pub cfg: SimulationConfig,
    seed: [u8; 32],
    pub rng: SimRng,
    pub frame: u64,
    pub paused: bool,
    pub nutrients: NutrientFields,
    pub chemistry: ChemistryGrid,
    pub signals: SignalField,
    pub memory: GrowthMemory,
    pub tips: Vec<HyphaTip>,
    pub organisms: Vec<OrganismInstance>,
    next_tip_id: u32,
    next_org_id: u32,
    pub events: Vec<String>,
    /// Scratch: tip count per cell for density inhibition
    density: Vec<u32>,
}

impl World {
    pub fn new(seed: [u8; 32], cfg: SimulationConfig) -> Self {
        let rng = rng_from_seed(&seed);
        let nutrients = NutrientFields::new(&cfg, 1.0, 0.6);
        let mut chemistry = ChemistryGrid::new(&cfg);
        // baseline substrates (agar) — concentrations are normalized 0..1 scale
        chemistry.set_uniform(chemistry::GLUCOSE, 0.4);
        chemistry.set_uniform(chemistry::OXYGEN, 0.35);
        chemistry.set_uniform(chemistry::AMMONIUM, 0.2);
        let mut w = Self {
            cfg: cfg.clone(),
            seed,
            rng,
            frame: 0,
            paused: false,
            nutrients,
            chemistry,
            signals: SignalField::new(&cfg),
            memory: GrowthMemory::new(&cfg),
            tips: Vec::new(),
            organisms: Vec::new(),
            next_tip_id: 1,
            next_org_id: 1,
            events: Vec::new(),
            density: vec![0; cfg.cell_count()],
        };
        w.bootstrap_inoculum();
        w
    }

    fn bootstrap_inoculum(&mut self) {
        let cx = self.cfg.grid_w as f32 * 0.5;
        let cy = self.cfg.grid_h as f32 * 0.5;
        self.tips.push(HyphaTip::new(
            self.next_tip_id,
            cx,
            cy,
            0.0,
            1,
        ));
        self.next_tip_id += 1;
        // Species ids are opaque keys — UI loads display names from MINDEX
        self.organisms.push(OrganismInstance::new(
            self.next_org_id,
            OrganismClass::Fungi,
            "mindex:species:fungi_placeholder",
            cx,
            cy,
        ));
        self.next_org_id += 1;
        self.organisms.push(OrganismInstance::new(
            self.next_org_id,
            OrganismClass::Bacteria,
            "mindex:species:bacteria_placeholder",
            cx + 8.0,
            cy - 6.0,
        ));
        self.next_org_id += 1;
        self.organisms.push(OrganismInstance::new(
            self.next_org_id,
            OrganismClass::HostCell,
            "mindex:species:host_placeholder",
            cx - 10.0,
            cy + 4.0,
        ));
        self.next_org_id += 1;
        self.push_event("bootstrap_inoculum");
    }

    fn push_event(&mut self, msg: impl Into<String>) {
        let s = msg.into();
        if self.events.len() > 500 {
            self.events.drain(0..100);
        }
        self.events.push(format!("[{}] {}", self.frame, s));
    }

    pub fn reset(&mut self, seed: [u8; 32]) {
        let cfg = self.cfg.clone();
        *self = World::new(seed, cfg);
    }

    pub fn set_seed(&mut self, seed: [u8; 32]) {
        self.seed = seed;
        self.rng = rng_from_seed(&seed);
    }

    pub fn snapshot(&self) -> StateSnapshot {
        let mut chemistry_means = [0.0f32; chemistry::N_COMPOUNDS];
        for c in 0..chemistry::N_COMPOUNDS {
            chemistry_means[c] = self.chemistry.mean_compound(c);
        }
        let mut sugar = 0.0f32;
        let mut nit = 0.0f32;
        let n = self.nutrients.sugar.len() as f32;
        for i in 0..self.nutrients.sugar.len() {
            sugar += self.nutrients.sugar[i];
            nit += self.nutrients.nitrogen[i];
        }
        StateSnapshot {
            frame: self.frame,
            paused: self.paused,
            seed_hex: hex32(&self.seed),
            tip_count: self.tips.iter().filter(|t| t.alive).count(),
            organism_count: self.organisms.len(),
            mean_sugar: sugar / n,
            mean_nitrogen: nit / n,
            chemistry_means,
            tips: self.tips.clone(),
            organisms: self.organisms.clone(),
            events_tail: self.events.iter().rev().take(32).cloned().rev().collect(),
        }
    }

    pub fn step(&mut self) {
        if self.paused {
            return;
        }
        let cfg = self.cfg.clone();
        self.nutrients
            .diffuse(cfg.nutrient_diffusion, cfg.nitrogen_diffusion);
        let diff = [0.15f32; chemistry::N_COMPOUNDS];
        let decay = [0.001f32; chemistry::N_COMPOUNDS];
        self.chemistry.diffuse_compounds(&diff, &decay);
        self.chemistry.ambient_step(DT);
        self.signals
            .decay_and_diffuse(cfg.signal_decay, 0.08);
        self.memory.decay(cfg.memory_decay);

        // rebuild density
        for d in &mut self.density {
            *d = 0;
        }
        let _w = cfg.grid_w as usize;
        for t in &self.tips {
            if !t.alive {
                continue;
            }
            let xi = t.x as i32;
            let yi = t.y as i32;
            if let Some(i) = self.nutrients.idx(xi, yi) {
                self.density[i] = self.density[i].saturating_add(1);
            }
        }

        let tips_len = self.tips.len();
        let mut new_tips: Vec<HyphaTip> = Vec::new();
        for idx in 0..tips_len {
            if !self.tips[idx].alive {
                continue;
            }
            let tip_id = self.tips[idx].id;
            let tip_x = self.tips[idx].x;
            let tip_y = self.tips[idx].y;
            let tip_angle = self.tips[idx].angle;
            let tip_energy = self.tips[idx].energy;
            let tip_age = self.tips[idx].age;
            let tip_lineage = self.tips[idx].lineage;

            let xi = tip_x as i32;
            let yi = tip_y as i32;
            let dens = self
                .nutrients
                .idx(xi, yi)
                .map(|i| self.density[i] as f32)
                .unwrap_or(0.0);
            let inhibit = 1.0 / (1.0 + dens * cfg.density_inhibition);

            let (sug, nit) = self.nutrients.sample(tip_x, tip_y);
            let mem = self.memory.sample(xi, yi);
            let sig = self
                .signals
                .idx(xi, yi)
                .map(|i| self.signals.level[i])
                .unwrap_or(0.0);

            let uptake = 0.04 * inhibit * (0.3 + mem + sig * 0.1);
            self.nutrients.consume_at(xi, yi, uptake * sug, uptake * nit * 0.5);
            self.chemistry
                .add_at(chemistry::GLUCOSE, xi, yi, -uptake * 0.01);

            let cos_a = tip_angle.cos();
            let sin_a = tip_angle.sin();
            let speed = cfg.tip_speed * (0.2 + sug) * inhibit;
            let nx = (tip_x + cos_a * speed).clamp(1.0, cfg.grid_w as f32 - 2.0);
            let ny = (tip_y + sin_a * speed).clamp(1.0, cfg.grid_h as f32 - 2.0);

            let mut energy = tip_energy - cfg.energy_decay_per_step + sug * 0.008;
            energy = (energy + sig * 0.001).min(2.0);
            let age = tip_age + 1;

            let angle = tip_angle + (self.rng.gen::<f32>() - 0.5) * 0.12;

            if age > cfg.senescence_age || energy <= 0.05 {
                self.tips[idx].alive = false;
                self.push_event(format!("senescence tip {}", tip_id));
                continue;
            }

            // branch
            if self.rng.gen::<f32>() < cfg.branch_probability * (0.5 + sug) {
                let branch_angle = angle + (self.rng.gen::<f32>() - 0.5) * 1.2;
                new_tips.push(HyphaTip::new(
                    self.next_tip_id,
                    nx,
                    ny,
                    branch_angle,
                    tip_lineage,
                ));
                self.push_event(format!("branch tip {}", self.next_tip_id));
                self.next_tip_id += 1;
                self.signals.pulse(xi, yi, 0.15);
            }

            if sug > 0.25 {
                self.memory.reinforce(xi, yi, 0.002);
            }

            self.tips[idx].x = nx;
            self.tips[idx].y = ny;
            self.tips[idx].angle = angle;
            self.tips[idx].energy = energy;
            self.tips[idx].age = age;
        }
        self.tips.extend(new_tips);

        anastomosis(&mut self.tips, cfg.anastomosis_radius);

        // organisms
        let hosts: Vec<_> = self
            .organisms
            .iter()
            .filter(|o| o.class == OrganismClass::HostCell)
            .cloned()
            .collect();

        let env: Vec<(f32, f32, f32, f32)> = self
            .organisms
            .iter()
            .map(|o| {
                let sug = sug_for(self, o.x, o.y);
                let gx = self
                    .chemistry
                    .sample_linear(chemistry::GLUCOSE, o.x, o.y);
                let ox = self
                    .chemistry
                    .sample_linear(chemistry::OXYGEN, o.x, o.y);
                let sec = self
                    .chemistry
                    .sample_linear(chemistry::SECONDARY_METABOLITE, o.x, o.y);
                (sug, gx, ox, sec)
            })
            .collect();

        for (i, o) in self.organisms.iter_mut().enumerate() {
            let (sug, gx, ox, sec) = env[i];
            match o.class {
                OrganismClass::Fungi => fungi::step_growth(o, (sug + gx) * 0.5, DT),
                OrganismClass::Mold => mold::step_growth(o, gx, DT),
                OrganismClass::Mildew => mildew::step_growth(o, gx, DT),
                OrganismClass::Bacteria => bacteria::step_growth(o, gx, ox, DT),
                OrganismClass::HostCell => cells::step_host(o, gx, DT),
                OrganismClass::Virus => virus::step_viral(o, &hosts, sec, DT),
            }
        }

        self.frame += 1;
    }
}

fn sug_for(w: &World, x: f32, y: f32) -> f32 {
    let xi = x as i32;
    let yi = y as i32;
    w.nutrients.idx(xi, yi)
        .map(|i| w.nutrients.sugar[i])
        .unwrap_or(0.0)
}

fn hex32(s: &[u8; 32]) -> String {
    s.iter().map(|b| format!("{:02x}", b)).collect()
}
