//! Mold — rapid radial expansion.

use super::OrganismInstance;

pub fn step_growth(o: &mut OrganismInstance, sugar: f32, dt: f32) {
    let g = sugar * 0.035 * dt * 60.0;
    o.biomass = (o.biomass + g).min(12.0);
    o.radius = (o.radius + g * 0.25).min(50.0);
}
