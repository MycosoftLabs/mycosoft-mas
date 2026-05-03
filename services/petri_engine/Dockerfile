# Petri Dish v2 — headless Rust engine (MAS repo: build from this directory)
# docker build -t mycosoft/petri-engine:v2 .
# docker run -p 8050:8050 -e PETRI_ENGINE_PORT=8050 mycosoft/petri-engine:v2
FROM rust:1.83-bookworm AS builder
WORKDIR /build
COPY Cargo.toml ./
COPY src ./src
COPY bin ./bin
RUN cargo build --release --features server --bin petri_engine_service

FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/petri_engine_service /usr/local/bin/petri_engine_service
ENV PETRI_ENGINE_PORT=8050
EXPOSE 8050
USER nobody
CMD ["/usr/local/bin/petri_engine_service"]
