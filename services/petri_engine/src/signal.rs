//! Inter-hyphal signal propagation (simplified pulse field on grid).

use crate::config::SimulationConfig;

pub struct SignalField {
    pub level: Vec<f32>,
    w: u32,
    h: u32,
}

impl SignalField {
    pub fn new(cfg: &SimulationConfig) -> Self {
        let n = cfg.cell_count();
        Self {
            level: vec![0.0; n],
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

    pub fn pulse(&mut self, x: i32, y: i32, strength: f32) {
        if let Some(i) = self.idx(x, y) {
            self.level[i] += strength;
        }
    }

    pub fn decay_and_diffuse(&mut self, decay: f32, diffuse: f32) {
        let w = self.w as usize;
        let h = self.h as usize;
        let mut n = self.level.clone();
        for y in 1..h - 1 {
            for x in 1..w - 1 {
                let i = y * w + x;
                let lap = self.level[i - 1] + self.level[i + 1] + self.level[i - w] + self.level[i + w]
                    - 4.0 * self.level[i];
                n[i] = (self.level[i] * decay + diffuse * lap).max(0.0);
            }
        }
        self.level = n;
    }
}
