//! Bacterial colonies — division / biofilm proxy via radius.

use super::OrganismInstance;

pub fn step_growth(o: &mut OrganismInstance, glucose: f32, oxygen: f32, dt: f32) {
    let g = glucose.min(oxygen * 2.0) * 0.03 * dt * 60.0;
    o.biomass = (o.biomass + g).min(6.0);
    o.radius = (o.radius + g * 0.08).min(25.0);
}
