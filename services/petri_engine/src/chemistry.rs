//! 16-compound reaction–diffusion layer + pH, temperature, light fields.

use crate::config::SimulationConfig;

pub const N_COMPOUNDS: usize = 16;

// Indices (aligned with plan taxonomy)
pub const GLUCOSE: usize = 0;
pub const FRUCTOSE: usize = 1;
pub const LACTOSE: usize = 2;
pub const AMMONIUM: usize = 3;
pub const NITRATE: usize = 4;
pub const OXYGEN: usize = 5;
pub const LACCASE: usize = 6;
pub const CELLULASE: usize = 7;
pub const XYLANASE: usize = 8;
pub const AMYLASE: usize = 9;
pub const PECTINASE: usize = 10;
pub const PROTEASE: usize = 11;
pub const EXOPOLYSACCHARIDE: usize = 12;
pub const SECONDARY_METABOLITE: usize = 13;
pub const AUTOINDUCER: usize = 14;
pub const DANGER_PEPTIDE: usize = 15;

pub struct ChemistryGrid {
    /// `compounds[c * ncells + cell]` — compound-major blocks for cache-friendly diffusion per compound
    pub compounds: Vec<f32>,
    pub ph: Vec<f32>,
    pub temperature: Vec<f32>,
    pub light: Vec<f32>,
    w: u32,
    h: u32,
    ncells: usize,
}

impl ChemistryGrid {
    pub fn new(cfg: &SimulationConfig) -> Self {
        let n = cfg.cell_count();
        Self {
            compounds: vec![0.0; n * N_COMPOUNDS],
            ph: vec![7.0; n],
            temperature: vec![37.0; n],
            light: vec![0.5; n],
            w: cfg.grid_w,
            h: cfg.grid_h,
            ncells: n,
        }
    }

    fn idx_cell(&self, x: i32, y: i32) -> Option<usize> {
        if x < 0 || y < 0 || x >= self.w as i32 || y >= self.h as i32 {
            return None;
        }
        Some((y as u32 * self.w + x as u32) as usize)
    }

    fn lin(&self, compound: usize, cell: usize) -> usize {
        compound * self.ncells + cell
    }

    /// Bilinear-ish nearest-cell sample for coupling organisms to fields.
    pub fn sample_linear(&self, compound: usize, x: f32, y: f32) -> f32 {
        let xi = (x.floor() as i32).clamp(0, self.w as i32 - 1);
        let yi = (y.floor() as i32).clamp(0, self.h as i32 - 1);
        self.idx_cell(xi, yi)
            .map(|cell| self.compounds[self.lin(compound, cell)])
            .unwrap_or(0.0)
    }

    pub fn set_uniform(&mut self, compound: usize, v: f32) {
        for c in 0..self.ncells {
            self.compounds[self.lin(compound, c)] = v;
        }
    }

    pub fn diffuse_compounds(&mut self, diffusion: &[f32; N_COMPOUNDS], decay: &[f32; N_COMPOUNDS]) {
        let w = self.w as usize;
        let h = self.h as usize;
        let n = self.ncells;
        let mut next = self.compounds.clone();
        for comp in 0..N_COMPOUNDS {
            let d = diffusion[comp].min(0.49);
            let k = decay[comp];
            for y in 1..h - 1 {
                for x in 1..w - 1 {
                    let cell = y * w + x;
                    let i = self.lin(comp, cell);
                    let lap = self.compounds[self.lin(comp, cell - 1)]
                        + self.compounds[self.lin(comp, cell + 1)]
                        + self.compounds[self.lin(comp, cell - w)]
                        + self.compounds[self.lin(comp, cell + w)]
                        - 4.0 * self.compounds[i];
                    let v = self.compounds[i] + d * lap;
                    next[i] = (v * (1.0 - k)).max(0.0);
                }
            }
        }
        self.compounds = next;
    }

    /// Simple Arrhenius-style modulation on glucose consumption regions (placeholder coupling).
    pub fn ambient_step(&mut self, dt: f32) {
        for i in 0..self.ncells {
            // gentle thermal drift
            self.temperature[i] += (self.light[i] - 0.5) * 0.001 * dt * 60.0;
            self.temperature[i] = self.temperature[i].clamp(20.0, 45.0);
            self.ph[i] += (self.compounds[self.lin(OXYGEN, i)] - 0.3) * 0.0001;
            self.ph[i] = self.ph[i].clamp(5.5, 8.5);
        }
    }

    pub fn add_at(&mut self, compound: usize, x: i32, y: i32, amount: f32) {
        if let Some(cell) = self.idx_cell(x, y) {
            let i = self.lin(compound, cell);
            self.compounds[i] += amount;
        }
    }

    pub fn mean_compound(&self, compound: usize) -> f32 {
        let mut s = 0.0f32;
        for c in 0..self.ncells {
            s += self.compounds[self.lin(compound, c)];
        }
        s / self.ncells as f32
    }
}
