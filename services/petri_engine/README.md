# petri_engine

Deterministic Rust core for **Virtual Petri Dish v2** (browser WASM + headless service).

## Build (native)

```bash
cd services/petri_engine
cargo test
cargo build --release --features server
```

## Run headless API (default port 8050)

```bash
PETRI_ENGINE_PORT=8050 cargo run --release --features server --bin petri_engine_service
```

Endpoints: `GET /health`, `GET /state`, `POST /step`, `POST /reset`, `POST /pause`, `POST /seed`, `GET /config`, `GET /ws` (WebSocket stream of JSON state).

## WASM (requires wasm-pack)

```bash
wasm-pack build --target web --features wasm --no-default-features -d ../../../WEBSITE/website/public/wasm/petri_engine
```

Or output to `lib/petri-dish-v2/wasm` per project conventions.

## Determinism

Uses `ChaCha8Rng` from a 32-byte seed; fixed `dt = 1/60`; identical `step()` on native and WASM for replay parity.
