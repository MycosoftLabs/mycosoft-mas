# PersonaPlex Docker Image for MYCA
# Date: January 27, 2026

FROM nvidia/cuda:12.1-runtime-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    libopus-dev \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone PersonaPlex repository
RUN git clone https://github.com/NVIDIA/personaplex.git /app/personaplex

# Install Python dependencies
WORKDIR /app/personaplex
RUN pip3 install --no-cache-dir ./moshi/.

# Install additional dependencies
RUN pip3 install --no-cache-dir accelerate websockets aiohttp httpx

# Copy MYCA persona configuration
COPY myca_persona.txt /app/myca_persona.txt
COPY start_server.sh /app/start_server.sh
RUN chmod +x /app/start_server.sh

EXPOSE 8998

ENV VOICE_PROMPT=NATF2.pt
ENV TEXT_PROMPT_FILE=/app/myca_persona.txt
ENV CPU_OFFLOAD=false

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -k -f https://localhost:8998/ || exit 1

CMD ["/app/start_server.sh"]
