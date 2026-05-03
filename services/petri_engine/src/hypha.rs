//! Hyphal tips: growth, branching, energy, senescence.

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct HyphaTip {
    pub id: u32,
    pub x: f32,
    pub y: f32,
    pub angle: f32,
    pub energy: f32,
    pub age: u32,
    pub alive: bool,
    pub lineage: u32,
}

impl HyphaTip {
    pub fn new(id: u32, x: f32, y: f32, angle: f32, lineage: u32) -> Self {
        Self {
            id,
            x,
            y,
            angle,
            energy: 1.0,
            age: 0,
            alive: true,
            lineage,
        }
    }
}

/// Try merge tips within radius (anastomosis) — fuse younger into older (deterministic).
pub fn anastomosis(tips: &mut [HyphaTip], radius: f32) {
    let n = tips.len();
    let mut fused = vec![false; n];
    for i in 0..n {
        if !tips[i].alive || fused[i] {
            continue;
        }
        for j in i + 1..n {
            if !tips[j].alive || fused[j] {
                continue;
            }
            let dx = tips[i].x - tips[j].x;
            let dy = tips[i].y - tips[j].y;
            if dx * dx + dy * dy <= radius * radius {
                if tips[i].age > tips[j].age
                    || (tips[i].age == tips[j].age && tips[i].id <= tips[j].id)
                {
                    tips[j].alive = false;
                    fused[j] = true;
                    tips[i].energy = (tips[i].energy + tips[j].energy * 0.5).min(1.5);
                } else {
                    tips[i].alive = false;
                    fused[i] = true;
                    tips[j].energy = (tips[j].energy + tips[i].energy * 0.5).min(1.5);
                    break;
                }
            }
        }
    }
}
