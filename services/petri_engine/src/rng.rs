//! Seeded RNG — ChaCha8 for reproducible WASM/native parity.

use rand::SeedableRng;
use rand_chacha::ChaCha8Rng;

pub type SimRng = ChaCha8Rng;

pub fn rng_from_seed(seed: &[u8; 32]) -> SimRng {
    SimRng::from_seed(*seed)
}
