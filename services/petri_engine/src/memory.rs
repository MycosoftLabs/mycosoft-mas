//! Spatial memory of favorable growth sites (decay + reinforcement).

use crate::config::SimulationConfig;

pub struct GrowthMemory {
    pub map: Vec<f32>,
    w: u32,
    h: u32,
}

impl GrowthMemory {
    pub fn new(cfg: &SimulationConfig) -> Self {
        Self {
            map: vec![0.0; cfg.cell_count()],
            w: cfg.grid_w,
            h: cfg.grid_h,
        }
    }

    pub fn idx(&self, x: i32, y: i32) -> Option<usize> {
        if x < 0 || y < 0 || x >= self.w as i32 || y >= self.h as i32 {
            return None;
        }
        Some((y as u32 * self.w + x as u32) as usize)
    }

    pub fn reinforce(&mut self, x: i32, y: i32, delta: f32) {
        if let Some(i) = self.idx(x, y) {
            self.map[i] = (self.map[i] + delta).min(1.0);
        }
    }

    pub fn decay(&mut self, factor: f32) {
        for v in &mut self.map {
            *v *= factor;
        }
    }

    pub fn sample(&self, x: i32, y: i32) -> f32 {
        self.idx(x, y).map(|i| self.map[i]).unwrap_or(0.0)
    }
}
