//! Headless Petri engine HTTP + WebSocket on port 8050 (override `PETRI_ENGINE_PORT`).

use std::env;
use std::net::SocketAddr;
use std::sync::Arc;

use axum::extract::ws::{Message, WebSocket, WebSocketUpgrade};
use axum::extract::State;
use axum::routing::get;
use axum::{Json, Router};
use petri_engine::{SimulationConfig, StateSnapshot, World};
use serde::Deserialize;
use tokio::sync::Mutex;
use tower_http::cors::CorsLayer;

#[derive(Clone)]
struct AppState {
    world: Arc<Mutex<World>>,
}

#[tokio::main]
async fn main() {
    let seed = default_seed();
    let world = World::new(seed, SimulationConfig::default());
    let state = AppState {
        world: Arc::new(Mutex::new(world)),
    };

    let app = Router::new()
        .route("/health", get(health))
        .route("/state", get(get_state))
        .route("/step", axum::routing::post(step))
        .route("/reset", axum::routing::post(reset))
        .route("/pause", axum::routing::post(pause_handler))
        .route("/seed", axum::routing::post(seed_handler))
        .route("/config", get(get_config))
        .route("/ws/stream", get(ws_stream))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let port: u16 = env::var("PETRI_ENGINE_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(8050);
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    eprintln!("petri_engine_service listening on http://{}", addr);
    axum::serve(listener, app).await.unwrap();
}

fn default_seed() -> [u8; 32] {
    let mut s = [0u8; 32];
    s[0] = 0x4d;
    s[1] = 0x79;
    s[2] = 0x63;
    s[3] = 0x6f;
    s[4] = 0x73;
    s[5] = 0x6f;
    s[6] = 0x66;
    s[7] = 0x74;
    s
}

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "ok",
        "service": "petri_engine_service",
        "version": env!("CARGO_PKG_VERSION"),
    }))
}

async fn get_state(State(st): State<AppState>) -> Json<StateSnapshot> {
    let w = st.world.lock().await;
    Json(w.snapshot())
}

#[derive(Deserialize)]
struct StepBody {
    pub n: Option<u64>,
}

async fn step(State(st): State<AppState>, Json(body): Json<StepBody>) -> Json<StateSnapshot> {
    let n = body.n.unwrap_or(1).min(3600);
    let mut w = st.world.lock().await;
    for _ in 0..n {
        w.step();
    }
    Json(w.snapshot())
}

#[derive(Deserialize)]
struct SeedBody {
    pub seed_hex: Option<String>,
}

async fn reset(State(st): State<AppState>, Json(body): Json<SeedBody>) -> Json<StateSnapshot> {
    let seed = parse_seed_hex(body.seed_hex.as_deref());
    let mut w = st.world.lock().await;
    w.reset(seed);
    Json(w.snapshot())
}

async fn pause_handler(
    State(st): State<AppState>,
    Json(body): Json<PauseBody>,
) -> Json<StateSnapshot> {
    let mut w = st.world.lock().await;
    w.paused = body.paused;
    Json(w.snapshot())
}

#[derive(Deserialize)]
struct PauseBody {
    paused: bool,
}

async fn seed_handler(
    State(st): State<AppState>,
    Json(body): Json<SeedBody>,
) -> Json<StateSnapshot> {
    let seed = parse_seed_hex(body.seed_hex.as_deref());
    let mut w = st.world.lock().await;
    w.set_seed(seed);
    Json(w.snapshot())
}

fn parse_seed_hex(hex: Option<&str>) -> [u8; 32] {
    let mut out = [0u8; 32];
    let Some(h) = hex else {
        return out;
    };
    let h = h.trim_start_matches("0x");
    let bytes: Vec<u8> = (0..h.len())
        .step_by(2)
        .filter_map(|i| u8::from_str_radix(h.get(i..i + 2)?, 16).ok())
        .collect();
    let n = bytes.len().min(32);
    out[..n].copy_from_slice(&bytes[..n]);
    out
}

async fn get_config(State(st): State<AppState>) -> Json<SimulationConfig> {
    let w = st.world.lock().await;
    Json(w.cfg.clone())
}

async fn ws_stream(ws: WebSocketUpgrade, State(st): State<AppState>) -> axum::response::Response {
    ws.on_upgrade(move |socket| handle_ws(socket, st))
}

async fn handle_ws(mut socket: WebSocket, st: AppState) {
    loop {
        let text = {
            let w = st.world.lock().await;
            serde_json::to_string(&w.snapshot()).unwrap_or_else(|_| "{}".into())
        };
        if socket.send(Message::Text(text)).await.is_err() {
            break;
        }
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
    }
}
