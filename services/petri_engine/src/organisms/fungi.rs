//! Fungal colony parameters — growth couples to hyphal tips (driven in `world`).

use super::OrganismInstance;

pub fn step_growth(o: &mut OrganismInstance, nutrient_sample: f32, dt: f32) {
    let g = nutrient_sample * 0.02 * dt * 60.0;
    o.biomass = (o.biomass + g).min(10.0);
    o.radius = (o.radius + g * 0.15).min(40.0);
}
