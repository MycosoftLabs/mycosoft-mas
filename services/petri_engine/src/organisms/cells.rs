//! Cultured host cells — substrate for viruses.

use super::OrganismInstance;

pub fn step_host(o: &mut OrganismInstance, glucose: f32, dt: f32) {
    let g = glucose * 0.012 * dt * 60.0;
    o.biomass = (o.biomass + g).min(5.0);
    o.radius = (o.radius + g * 0.05).min(18.0);
}
