# Model Training Container for NLM
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential git curl wget libgl1-mesa-glx graphviz && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch torchvision torchaudio numpy pandas scikit-learn matplotlib seaborn plotly tensorboard wandb jupyter fastapi uvicorn
RUN mkdir -p /app/data /app/models /app/logs /app/notebooks
EXPOSE 8000 8888 6006
CMD ["python", "-m", "uvicorn", "training_api:app", "--host", "0.0.0.0", "--port", "8000"]
