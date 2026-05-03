//! Petri Dish v2 simulation core — WASM (`wasm`) and native (`server`) / library (`rlib`).

pub mod chemistry;
pub mod config;
pub mod hypha;
pub mod memory;
pub mod nutrients;
pub mod organisms;
pub mod rng;
pub mod signal;
pub mod world;

pub use config::SimulationConfig;
pub use world::{StateSnapshot, World};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn deterministic_same_seed() {
        let seed = [42u8; 32];
        let cfg = SimulationConfig {
            grid_w: 48,
            grid_h: 48,
            ..Default::default()
        };
        let mut a = World::new(seed, cfg.clone());
        let mut b = World::new(seed, cfg);
        for _ in 0..80 {
            a.step();
            b.step();
        }
        let sa = serde_json::to_string(&a.snapshot()).unwrap();
        let sb = serde_json::to_string(&b.snapshot()).unwrap();
        assert_eq!(sa, sb);
    }
}

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

/// WASM-facing simulation handle (single-threaded).
#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub struct WasmSimulation {
    inner: World,
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
impl WasmSimulation {
    #[wasm_bindgen(constructor)]
    pub fn new(seed_bytes: &[u8]) -> WasmSimulation {
        let mut seed = [0u8; 32];
        let n = seed_bytes.len().min(32);
        seed[..n].copy_from_slice(&seed_bytes[..n]);
        WasmSimulation {
            inner: World::new(seed, SimulationConfig::default()),
        }
    }

    pub fn step(&mut self) {
        self.inner.step();
    }

    pub fn frame(&self) -> u64 {
        self.inner.frame
    }

    pub fn state_json(&self) -> String {
        serde_json::to_string(&self.inner.snapshot()).unwrap_or_else(|_| "{}".into())
    }

    pub fn reset(&mut self, seed_bytes: &[u8]) {
        let mut seed = [0u8; 32];
        let n = seed_bytes.len().min(32);
        seed[..n].copy_from_slice(&seed_bytes[..n]);
        self.inner.reset(seed);
    }

    pub fn set_paused(&mut self, paused: bool) {
        self.inner.paused = paused;
    }
}
