//! Simulation configuration (extended from mycorust-style parameters).

use serde::{Deserialize, Serialize};

/// Fixed integration timestep (seconds) — matches 60 Hz tick for determinism.
pub const DT: f32 = 1.0 / 60.0;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SimulationConfig {
    pub grid_w: u32,
    pub grid_h: u32,
    /// Hypha tip movement per step (grid cells, fractional accumulated internally).
    pub tip_speed: f32,
    pub branch_probability: f32,
    pub nutrient_diffusion: f32,
    pub nitrogen_diffusion: f32,
    pub energy_decay_per_step: f32,
    pub senescence_age: u32,
    pub anastomosis_radius: f32,
    pub density_inhibition: f32,
    pub signal_decay: f32,
    pub memory_decay: f32,
}

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            grid_w: 128,
            grid_h: 128,
            tip_speed: 0.35,
            branch_probability: 0.08,
            nutrient_diffusion: 0.22,
            nitrogen_diffusion: 0.18,
            energy_decay_per_step: 0.002,
            senescence_age: 4000,
            anastomosis_radius: 2.5,
            density_inhibition: 0.15,
            signal_decay: 0.94,
            memory_decay: 0.999,
        }
    }
}

impl SimulationConfig {
    pub fn cell_count(&self) -> usize {
        (self.grid_w * self.grid_h) as usize
    }
}
