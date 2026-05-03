//! Nutrient grids (sugar + nitrogen) with explicit FTCS diffusion.

use crate::config::SimulationConfig;

pub struct NutrientFields {
    pub sugar: Vec<f32>,
    pub nitrogen: Vec<f32>,
    w: u32,
    h: u32,
}

impl NutrientFields {
    pub fn new(cfg: &SimulationConfig, initial_sugar: f32, initial_nitrogen: f32) -> Self {
        let n = cfg.cell_count();
        Self {
            sugar: vec![initial_sugar; n],
            nitrogen: vec![initial_nitrogen; n],
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

    pub fn diffuse(&mut self, ds: f32, dn: f32) {
        let w = self.w as usize;
        let h = self.h as usize;
        let mut ns = self.sugar.clone();
        let mut nn = self.nitrogen.clone();
        for y in 1..h - 1 {
            for x in 1..w - 1 {
                let i = y * w + x;
                let lap_s = self.sugar[i - 1] + self.sugar[i + 1] + self.sugar[i - w]
                    + self.sugar[i + w]
                    - 4.0 * self.sugar[i];
                let lap_n = self.nitrogen[i - 1] + self.nitrogen[i + 1] + self.nitrogen[i - w]
                    + self.nitrogen[i + w]
                    - 4.0 * self.nitrogen[i];
                ns[i] = (self.sugar[i] + ds * lap_s).max(0.0);
                nn[i] = (self.nitrogen[i] + dn * lap_n).max(0.0);
            }
        }
        self.sugar = ns;
        self.nitrogen = nn;
    }

    pub fn consume_at(&mut self, x: i32, y: i32, sugar_amt: f32, n_amt: f32) {
        if let Some(i) = self.idx(x, y) {
            self.sugar[i] = (self.sugar[i] - sugar_amt).max(0.0);
            self.nitrogen[i] = (self.nitrogen[i] - n_amt).max(0.0);
        }
    }

    pub fn sample(&self, x: f32, y: f32) -> (f32, f32) {
        let xi = x.clamp(0.0, self.w as f32 - 1.001) as i32;
        let yi = y.clamp(0.0, self.h as f32 - 1.001) as i32;
        if let Some(i) = self.idx(xi, yi) {
            (self.sugar[i], self.nitrogen[i])
        } else {
            (0.0, 0.0)
        }
    }
}
