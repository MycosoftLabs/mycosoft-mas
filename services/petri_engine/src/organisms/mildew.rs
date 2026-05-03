//! Mildew — surface-biased growth (same radial model, lower rate).

use super::OrganismInstance;

pub fn step_growth(o: &mut OrganismInstance, sugar: f32, dt: f32) {
    let g = sugar * 0.018 * dt * 60.0;
    o.biomass = (o.biomass + g).min(8.0);
    o.radius = (o.radius + g * 0.12).min(35.0);
}
