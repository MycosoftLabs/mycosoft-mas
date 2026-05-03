//! Viruses / phages — require host proximity; latent → lytic burst proxy.

use super::{OrganismClass, OrganismInstance};

pub fn step_viral(
    o: &mut OrganismInstance,
    hosts: &[OrganismInstance],
    secondary_metabolite: f32,
    dt: f32,
) {
    let mut near = 0.0f32;
    for h in hosts {
        if h.class != OrganismClass::HostCell {
            continue;
        }
        let dx = o.x - h.x;
        let dy = o.y - h.y;
        let d = (dx * dx + dy * dy).sqrt();
        if d < h.radius + 2.0 {
            near += h.biomass / (1.0 + d);
        }
    }
    if o.latent {
        if near > 0.2 {
            o.latent = false;
        }
    } else {
        let burst = secondary_metabolite * 0.01 * dt * 60.0;
        o.biomass = (o.biomass + near * 0.005 * dt * 60.0 - burst).max(0.01);
        if o.biomass > 0.5 {
            o.biomass *= 0.6;
            o.radius = (o.radius + 0.4).min(6.0);
        }
    }
}
