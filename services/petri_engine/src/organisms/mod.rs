//! Microbiome organism classes — integrated into `World::step`.

pub mod bacteria;
pub mod cells;
pub mod fungi;
pub mod mildew;
pub mod mold;
pub mod virus;

use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganismClass {
    Fungi,
    Mold,
    Mildew,
    Bacteria,
    Virus,
    HostCell,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct OrganismInstance {
    pub id: u32,
    pub class: OrganismClass,
    pub species_id: String,
    pub x: f32,
    pub y: f32,
    pub radius: f32,
    pub biomass: f32,
    pub latent: bool,
}

impl OrganismInstance {
    pub fn new(
        id: u32,
        class: OrganismClass,
        species_id: impl Into<String>,
        x: f32,
        y: f32,
    ) -> Self {
        let (radius, biomass) = match class {
            OrganismClass::Fungi => (1.2, 0.5),
            OrganismClass::Mold => (2.0, 0.3),
            OrganismClass::Mildew => (1.5, 0.25),
            OrganismClass::Bacteria => (0.8, 0.15),
            OrganismClass::Virus => (0.2, 0.02),
            OrganismClass::HostCell => (1.0, 0.4),
        };
        Self {
            id,
            class,
            species_id: species_id.into(),
            x,
            y,
            radius,
            biomass,
            latent: matches!(class, OrganismClass::Virus),
        }
    }
}
