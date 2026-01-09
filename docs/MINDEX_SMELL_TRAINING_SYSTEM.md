# MINDEX Automated Smell Training System

## The World's Largest Fungal Smell Register

**Date**: 2026-01-09  
**Status**: Design Document  
**Author**: Mycosoft AI Team

---

## Executive Summary

This document outlines a comprehensive system to create the **world's largest fungal smell database** within MINDEX, leveraging automated data collection from BME688/BME690 sensors, Bosch AI-Studio integration, and AI-powered training workflows.

### Key Goals

1. **Automated Smell Training**: Real-time collection and training using MycoBrain devices
2. **MINDEX Smell Registry**: Centralized blob storage and management
3. **Rapid Blob Generation**: Automated workflows for creating new BSEC selectivity configs
4. **Community Contribution**: Open protocols for researchers worldwide
5. **AI-Studio Automation**: Desktop automation via Claude Computer Use or API

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MINDEX SMELL TRAINING SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   SENSORS    │    │  COLLECTION  │    │   TRAINING   │    │    MINDEX    │  │
│  │              │    │              │    │              │    │              │  │
│  │ BME688/690   │───▶│  Raw Data    │───▶│  AI-Studio   │───▶│  Blob Store  │  │
│  │ + MycoBrain  │    │  Pipeline    │    │  Automation  │    │  + Registry  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │                   │          │
│         ▼                   ▼                   ▼                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Lab Hardware │    │   FastAPI    │    │    Bosch     │    │  PostgreSQL  │  │
│  │ + Specimens  │    │   Service    │    │   AI-Studio  │    │  + MinIO S3  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           AUTOMATION LAYER                               │   │
│  │                                                                          │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │   │
│  │  │ Claude       │    │ Edge Impulse │    │ Alternative  │               │   │
│  │  │ Desktop Use  │    │ ML Training  │    │ ML Pipelines │               │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. BME688 Sensor Overview

Based on the [Bosch BME688 Datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme688-ds000.pdf):

### Key Capabilities

| Feature | Value |
|---------|-------|
| VOC Detection | ppb (parts per billion) range |
| Gases Detected | VOCs, VSCs, CO, H₂ |
| AI Integration | Built-in gas scanner with customizable ML |
| F1 Score (H₂S) | 0.94 |
| Scan Speed | 10.8s per scan |
| Power Consumption | < 0.1mA ultra-low power mode |

### BSEC2 Outputs

| Output | Description |
|--------|-------------|
| IAQ | Indoor Air Quality (0-500) |
| Static IAQ | Calibrated IAQ |
| eCO₂ | CO₂ equivalent (ppm) |
| bVOC | Breath VOC equivalent (ppm) |
| Gas Estimates 1-4 | Custom class probabilities |
| Gas Resistance | Raw resistance (Ω) |

### Training Requirements

Per [PiCockpit Tutorial](https://picockpit.com/raspberry-pi/teach-bme688-how-to-smell/):

1. **Burn-in Period**: 24 hours minimum before data collection
2. **Multiple Sensors**: BME688 Development Kit has 8 sensors for faster acquisition
3. **Class Limit**: BSEC2 supports up to 4 custom gas classes
4. **Training Samples**: Minimum 50-100 samples per class recommended
5. **Environmental Control**: Consistent temperature/humidity during training

---

## 2. Data Collection Pipeline

### 2.1 Hardware Setup

```
Lab Training Station:
├── MycoBrain Board (ESP32-S3)
│   ├── BME688 #1 (0x77) - Ambient sensor
│   └── BME688 #2 (0x76) - Specimen sensor
├── Specimen Chamber
│   ├── Controlled airflow
│   ├── Humidity control
│   └── Sample positioning
├── Reference Sensors
│   ├── Temperature probe
│   └── Humidity probe
└── Computer
    ├── MycoBrain Service (FastAPI)
    ├── BME AI-Studio Desktop
    └── MINDEX Connection
```

### 2.2 Automated Data Collection Script

```python
# training_collector.py
import serial
import json
import time
from datetime import datetime
from pathlib import Path

class SmellTrainingCollector:
    """Automated smell training data collection for BME688."""
    
    def __init__(self, port: str = "COM7", baud: int = 115200):
        self.serial = serial.Serial(port, baud, timeout=1)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.data_dir = Path(f"training_data/{self.session_id}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def collect_sample(self, label: str, duration_sec: int = 60, 
                       interval_sec: float = 1.0) -> dict:
        """
        Collect training samples for a specific smell class.
        
        Args:
            label: Class label (e.g., "oyster_mushroom", "trichoderma")
            duration_sec: How long to collect (seconds)
            interval_sec: Time between samples
        """
        samples = []
        start_time = time.time()
        
        print(f"📊 Collecting samples for '{label}' - {duration_sec}s")
        
        while time.time() - start_time < duration_sec:
            # Request sensor data
            self.serial.write(b"sensors\n")
            time.sleep(0.3)
            
            response = self.serial.read_all().decode()
            
            # Parse JSON response
            for line in response.split("\n"):
                if line.startswith("{") and '"bme1"' in line:
                    try:
                        data = json.loads(line)
                        sample = {
                            "timestamp": datetime.now().isoformat(),
                            "label": label,
                            "bme1": data.get("bme1", {}),
                            "bme2": data.get("bme2", {}),
                        }
                        samples.append(sample)
                    except json.JSONDecodeError:
                        pass
            
            time.sleep(interval_sec)
        
        # Save to file
        output_file = self.data_dir / f"{label}_{len(samples)}_samples.json"
        with open(output_file, "w") as f:
            json.dump(samples, f, indent=2)
        
        print(f"✅ Saved {len(samples)} samples to {output_file}")
        return {"label": label, "count": len(samples), "file": str(output_file)}
    
    def collect_training_session(self, specimens: dict) -> list:
        """
        Collect a full training session with multiple specimens.
        
        Args:
            specimens: Dict of {label: {"duration": int, "description": str}}
        """
        results = []
        
        for label, config in specimens.items():
            print(f"\n🍄 Place specimen: {label}")
            print(f"   Description: {config.get('description', 'N/A')}")
            input("   Press ENTER when ready...")
            
            result = self.collect_sample(
                label=label,
                duration_sec=config.get("duration", 60)
            )
            results.append(result)
            
            print("   Remove specimen and ventilate...")
            time.sleep(10)  # Allow air to clear
        
        return results

# Example usage
if __name__ == "__main__":
    collector = SmellTrainingCollector(port="COM7")
    
    # Define training specimens
    specimens = {
        "clean_air": {
            "duration": 30,
            "description": "Baseline clean lab air"
        },
        "pleurotus_ostreatus": {
            "duration": 60,
            "description": "Fresh oyster mushroom fruiting body"
        },
        "lentinula_edodes": {
            "duration": 60,
            "description": "Fresh shiitake mushroom"
        },
        "trichoderma_viride": {
            "duration": 60,
            "description": "Trichoderma contamination sample"
        }
    }
    
    # Run collection
    results = collector.collect_training_session(specimens)
    print(f"\n📦 Session complete: {len(results)} specimens collected")
```

### 2.3 Data Format for AI-Studio

AI-Studio expects data in a specific format. Convert collected data:

```python
# convert_to_ai_studio.py
import json
import csv
from pathlib import Path

def convert_to_ai_studio_format(training_dir: str, output_file: str):
    """
    Convert training data to Bosch AI-Studio compatible format.
    
    AI-Studio expects:
    - CSV with columns: timestamp, class_label, gas_resistance, temperature, 
      humidity, pressure, heater_profile
    """
    training_path = Path(training_dir)
    all_samples = []
    
    for json_file in training_path.glob("*.json"):
        with open(json_file) as f:
            samples = json.load(f)
            all_samples.extend(samples)
    
    # Write CSV for AI-Studio
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "class_label", 
            "gas_resistance_amb", "temp_amb", "humidity_amb", "pressure_amb",
            "gas_resistance_env", "temp_env", "humidity_env", "pressure_env",
            "heater_temp", "heater_duration"
        ])
        
        for sample in all_samples:
            bme1 = sample.get("bme1", {})
            bme2 = sample.get("bme2", {})
            
            writer.writerow([
                sample["timestamp"],
                sample["label"],
                bme1.get("gas_ohm", 0),
                bme1.get("temp_c", 0),
                bme1.get("rh_pct", 0),
                bme1.get("press_hpa", 0),
                bme2.get("gas_ohm", 0),
                bme2.get("temp_c", 0),
                bme2.get("rh_pct", 0),
                bme2.get("press_hpa", 0),
                300,  # Default heater temp (°C)
                100   # Default heater duration (ms)
            ])
    
    print(f"✅ Exported {len(all_samples)} samples to {output_file}")
```

---

## 3. Bosch AI-Studio Automation

### 3.1 AI-Studio Overview

Bosch BME AI-Studio is a **desktop application** for training BME688 gas classification models. It does not have a public API, but offers:

- **Desktop Version**: Windows/macOS GUI application
- **Server Version**: For automated/headless training (enterprise)
- **Development Kit Integration**: Direct sensor connection

### 3.2 Automation Methods

#### Method 1: Claude Computer Use (Desktop Automation)

Use Claude's Computer Use capability to control AI-Studio:

```python
# ai_studio_automation.py
"""
Automation script for Bosch AI-Studio using Claude Computer Use.
This requires the Anthropic Computer Use API or similar desktop control.
"""

import anthropic
from pathlib import Path

class AIStudioAutomation:
    """Automate Bosch AI-Studio via Claude Computer Use."""
    
    def __init__(self):
        self.client = anthropic.Anthropic()
        
    async def import_training_data(self, csv_path: str):
        """Import training CSV into AI-Studio."""
        prompt = f"""
        You are controlling Bosch BME AI-Studio desktop application.
        
        Task: Import training data from {csv_path}
        
        Steps:
        1. Click "File" menu
        2. Select "Import Data"
        3. Navigate to {csv_path}
        4. Click "Open"
        5. Verify data appears in the data panel
        6. Report success
        """
        
        # Use Computer Use to execute
        # (Implementation depends on Computer Use API)
        pass
    
    async def train_model(self, class_labels: list, model_name: str):
        """Train a gas classification model."""
        prompt = f"""
        Train a new gas classification model in AI-Studio:
        
        1. Go to "Training" tab
        2. Select classes: {', '.join(class_labels)}
        3. Set model name: {model_name}
        4. Click "Start Training"
        5. Wait for training to complete
        6. Export configuration file
        """
        pass
    
    async def export_blob(self, output_path: str):
        """Export trained model as BSEC configuration blob."""
        prompt = f"""
        Export the trained model:
        
        1. Go to "Export" menu
        2. Select "BSEC Configuration File"
        3. Save to {output_path}
        4. Verify file is created
        """
        pass
```

#### Method 2: Server API (Enterprise)

Bosch offers AI-Studio Server for enterprise customers with REST API:

```python
# ai_studio_server.py (Requires enterprise license)
import requests
from pathlib import Path

class AIStudioServer:
    """Interface with AI-Studio Server API (enterprise)."""
    
    def __init__(self, server_url: str, api_key: str):
        self.base_url = server_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def upload_training_data(self, csv_path: str, project_id: str):
        """Upload training data to server."""
        with open(csv_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/api/projects/{project_id}/data",
                headers=self.headers,
                files={"file": f}
            )
        return response.json()
    
    def start_training(self, project_id: str, config: dict):
        """Start model training job."""
        response = requests.post(
            f"{self.base_url}/api/projects/{project_id}/train",
            headers=self.headers,
            json=config
        )
        return response.json()
    
    def get_training_status(self, job_id: str):
        """Check training job status."""
        response = requests.get(
            f"{self.base_url}/api/jobs/{job_id}",
            headers=self.headers
        )
        return response.json()
    
    def download_blob(self, model_id: str) -> bytes:
        """Download trained BSEC configuration."""
        response = requests.get(
            f"{self.base_url}/api/models/{model_id}/blob",
            headers=self.headers
        )
        return response.content
```

#### Method 3: Edge Impulse Alternative

Use [Edge Impulse](https://edgeimpulse.com) as an alternative ML training platform:

```python
# edge_impulse_training.py
"""
Alternative training pipeline using Edge Impulse.
Edge Impulse provides a full REST API for automated training.
"""

import requests
import json

class EdgeImpulseTrainer:
    """Train BME688 models using Edge Impulse platform."""
    
    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        self.base_url = "https://studio.edgeimpulse.com/v1/api"
        self.headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
    
    def upload_samples(self, samples: list, label: str):
        """Upload training samples to Edge Impulse."""
        for sample in samples:
            data = {
                "label": label,
                "data": {
                    "timestamp": sample["timestamp"],
                    "values": [
                        sample["bme1"]["gas_ohm"],
                        sample["bme1"]["temp_c"],
                        sample["bme1"]["rh_pct"],
                        sample["bme2"]["gas_ohm"],
                        sample["bme2"]["temp_c"],
                        sample["bme2"]["rh_pct"]
                    ]
                }
            }
            
            response = requests.post(
                f"{self.base_url}/{self.project_id}/training/data",
                headers=self.headers,
                json=data
            )
    
    def train_model(self):
        """Trigger model training."""
        response = requests.post(
            f"{self.base_url}/{self.project_id}/jobs/train",
            headers=self.headers,
            json={"epochs": 100, "learningRate": 0.001}
        )
        return response.json()
    
    def export_model(self, target: str = "esp32"):
        """Export trained model for deployment."""
        response = requests.post(
            f"{self.base_url}/{self.project_id}/deployment",
            headers=self.headers,
            json={"engine": "tflite", "target": target}
        )
        return response.content
```

---

## 4. MINDEX Blob Storage

### 4.1 Database Schema

```sql
-- MINDEX Smell Registry Database Schema

-- Smell Signatures (metadata)
CREATE TABLE smell_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,  -- fungal, plant, chemical, etc.
    subcategory VARCHAR(128),
    description TEXT,
    species_id UUID REFERENCES species(id),
    
    -- BSEC mapping
    bsec_class_id INTEGER,  -- 0-3 for 4-class system
    
    -- VOC fingerprint (JSON)
    voc_pattern JSONB NOT NULL DEFAULT '{}',
    
    -- Visual
    icon_type VARCHAR(32),
    color_hex VARCHAR(7),
    
    -- Training stats
    training_samples INTEGER DEFAULT 0,
    confidence_threshold DECIMAL(3,2) DEFAULT 0.75,
    
    -- Blob reference
    current_blob_id UUID REFERENCES smell_blobs(id),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(128),
    
    -- Indexes
    CONSTRAINT unique_smell_name UNIQUE(name, category)
);

-- BSEC Configuration Blobs
CREATE TABLE smell_blobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Blob metadata
    name VARCHAR(255) NOT NULL,
    version VARCHAR(32) NOT NULL,
    description TEXT,
    
    -- Training info
    training_date TIMESTAMP NOT NULL,
    training_samples INTEGER NOT NULL,
    training_duration_hours DECIMAL(5,2),
    training_method VARCHAR(64),  -- ai_studio, edge_impulse, custom
    
    -- Class mappings
    class_labels JSONB NOT NULL,  -- ["clean_air", "mushroom", "contamination", ...]
    class_count INTEGER NOT NULL,
    
    -- Blob data
    blob_data BYTEA NOT NULL,  -- The actual BSEC selectivity config
    blob_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash for integrity
    blob_size_bytes INTEGER NOT NULL,
    
    -- Compatibility
    bsec_version VARCHAR(16) NOT NULL,  -- e.g., "2.4.0"
    sensor_model VARCHAR(32) NOT NULL,  -- BME688, BME690
    
    -- Quality metrics
    f1_score DECIMAL(4,3),
    accuracy DECIMAL(4,3),
    confusion_matrix JSONB,
    
    -- Storage
    s3_bucket VARCHAR(255),
    s3_key VARCHAR(512),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(128),
    
    -- Status
    status VARCHAR(32) DEFAULT 'active',  -- active, deprecated, testing
    
    -- Indexes
    CONSTRAINT unique_blob_version UNIQUE(name, version)
);

-- Training Sessions
CREATE TABLE smell_training_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Session info
    session_name VARCHAR(255),
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(32) DEFAULT 'in_progress',
    
    -- Hardware
    device_id VARCHAR(64),  -- MycoBrain serial
    sensor_ids JSONB,  -- ["BME688-0x77", "BME688-0x76"]
    
    -- Environment
    lab_conditions JSONB,  -- {temp_c, humidity_pct, notes}
    
    -- Specimens
    specimens JSONB NOT NULL,  -- [{label, species_id, duration_sec, notes}]
    
    -- Results
    total_samples INTEGER DEFAULT 0,
    raw_data_path VARCHAR(512),
    
    -- Blob output
    output_blob_id UUID REFERENCES smell_blobs(id),
    
    -- Metadata
    created_by VARCHAR(128),
    notes TEXT
);

-- Training Samples (raw data)
CREATE TABLE smell_training_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES smell_training_sessions(id),
    
    -- Sample info
    timestamp TIMESTAMP NOT NULL,
    label VARCHAR(128) NOT NULL,
    
    -- Sensor readings
    gas_resistance_ohm DOUBLE PRECISION,
    temperature_c DOUBLE PRECISION,
    humidity_pct DOUBLE PRECISION,
    pressure_hpa DOUBLE PRECISION,
    
    -- BSEC outputs (if available)
    iaq DOUBLE PRECISION,
    co2_equivalent DOUBLE PRECISION,
    voc_equivalent DOUBLE PRECISION,
    
    -- Heater profile
    heater_temp_c INTEGER,
    heater_duration_ms INTEGER,
    
    -- Raw JSON
    raw_data JSONB
);

-- Create indexes
CREATE INDEX idx_smell_signatures_category ON smell_signatures(category);
CREATE INDEX idx_smell_signatures_species ON smell_signatures(species_id);
CREATE INDEX idx_smell_blobs_status ON smell_blobs(status);
CREATE INDEX idx_training_samples_session ON smell_training_samples(session_id);
CREATE INDEX idx_training_samples_label ON smell_training_samples(label);
```

### 4.2 Blob Storage API

```python
# mindex_smell_api.py
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import hashlib
import base64

app = FastAPI(title="MINDEX Smell Registry API")

class SmellBlobCreate(BaseModel):
    name: str
    version: str
    description: Optional[str]
    class_labels: List[str]
    training_samples: int
    bsec_version: str = "2.4.0"
    sensor_model: str = "BME688"
    f1_score: Optional[float]
    accuracy: Optional[float]

class SmellBlobResponse(BaseModel):
    id: str
    name: str
    version: str
    class_labels: List[str]
    blob_hash: str
    created_at: str

@app.post("/api/mindex/blobs", response_model=SmellBlobResponse)
async def upload_smell_blob(
    metadata: SmellBlobCreate,
    blob_file: UploadFile = File(...)
):
    """Upload a new BSEC selectivity blob to MINDEX."""
    
    # Read blob data
    blob_data = await blob_file.read()
    blob_hash = hashlib.sha256(blob_data).hexdigest()
    
    # Check for duplicates
    existing = await db.smell_blobs.find_one({"blob_hash": blob_hash})
    if existing:
        raise HTTPException(400, "Blob with this hash already exists")
    
    # Store in database
    blob_id = await db.smell_blobs.insert_one({
        "name": metadata.name,
        "version": metadata.version,
        "description": metadata.description,
        "class_labels": metadata.class_labels,
        "class_count": len(metadata.class_labels),
        "training_samples": metadata.training_samples,
        "bsec_version": metadata.bsec_version,
        "sensor_model": metadata.sensor_model,
        "blob_data": blob_data,
        "blob_hash": blob_hash,
        "blob_size_bytes": len(blob_data),
        "f1_score": metadata.f1_score,
        "accuracy": metadata.accuracy,
        "status": "active"
    })
    
    return SmellBlobResponse(
        id=str(blob_id),
        name=metadata.name,
        version=metadata.version,
        class_labels=metadata.class_labels,
        blob_hash=blob_hash,
        created_at=datetime.now().isoformat()
    )

@app.get("/api/mindex/blobs/{blob_id}")
async def get_smell_blob(blob_id: str):
    """Get blob metadata and download link."""
    blob = await db.smell_blobs.find_one({"_id": blob_id})
    if not blob:
        raise HTTPException(404, "Blob not found")
    return blob

@app.get("/api/mindex/blobs/{blob_id}/download")
async def download_smell_blob(blob_id: str, format: str = "binary"):
    """Download blob as binary or C header."""
    blob = await db.smell_blobs.find_one({"_id": blob_id})
    if not blob:
        raise HTTPException(404, "Blob not found")
    
    blob_data = blob["blob_data"]
    
    if format == "header":
        # Generate C/C++ header file
        header = generate_c_header(blob["name"], blob_data)
        return Response(
            content=header,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=bsec_selectivity.h"}
        )
    else:
        return Response(
            content=blob_data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={blob['name']}.config"}
        )

def generate_c_header(name: str, blob_data: bytes) -> str:
    """Generate C header file for Arduino/ESP32."""
    safe_name = name.replace("-", "_").replace(" ", "_").lower()
    
    # Format bytes as C array
    bytes_str = ",".join(str(b) for b in blob_data)
    
    return f"""#pragma once
#include <stdint.h>

// BSEC Selectivity Configuration: {name}
// Generated by MINDEX Smell Registry
// Blob size: {len(blob_data)} bytes

static const uint8_t bsec_selectivity_config[{len(blob_data)}] = {{
{bytes_str}
}};

static const size_t bsec_selectivity_config_len = sizeof(bsec_selectivity_config);
"""

@app.get("/api/mindex/blobs/search")
async def search_blobs(
    category: Optional[str] = None,
    species: Optional[str] = None,
    min_accuracy: Optional[float] = None
):
    """Search for smell blobs."""
    query = {"status": "active"}
    
    if min_accuracy:
        query["accuracy"] = {"$gte": min_accuracy}
    
    blobs = await db.smell_blobs.find(query).to_list(100)
    return blobs
```

---

## 5. Community Blob Sources

### 5.1 Known Blob Repositories

| Source | Description | URL |
|--------|-------------|-----|
| Bosch Reference | Default BSEC configs | Included with BSEC library |
| eNose Project | Community e-nose blobs | [github.com/AndyYuen/eNose](https://github.com/AndyYuen/eNose) |
| PiCockpit Examples | Raspberry Pi tutorials | [picockpit.com](https://picockpit.com) |
| Garret's Firmware | Working fungal blob | `startHERE_ESP32AB_BSEC2_WORKING_DUAL` |

### 5.2 Blob Aggregation Script

```python
# blob_aggregator.py
"""Aggregate BSEC blobs from community sources."""

import requests
import os
from pathlib import Path
import hashlib

class BlobAggregator:
    """Collect and organize BSEC blobs from various sources."""
    
    SOURCES = [
        {
            "name": "eNose Project",
            "type": "github",
            "repo": "AndyYuen/eNose",
            "path": "bsec/",
            "pattern": "*.config"
        },
        {
            "name": "Local Firmware",
            "type": "local",
            "path": "C:/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas/firmware",
            "pattern": "**/bsec_selectivity.*"
        }
    ]
    
    def __init__(self, output_dir: str = "collected_blobs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.collected = []
    
    def collect_from_github(self, repo: str, path: str, pattern: str):
        """Download blobs from GitHub repository."""
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
        response = requests.get(api_url)
        
        if response.status_code != 200:
            print(f"Failed to access {repo}")
            return
        
        for item in response.json():
            if item["type"] == "file":
                # Download file
                file_response = requests.get(item["download_url"])
                if file_response.status_code == 200:
                    blob_path = self.output_dir / f"{repo.replace('/', '_')}_{item['name']}"
                    blob_path.write_bytes(file_response.content)
                    self.collected.append({
                        "source": repo,
                        "name": item["name"],
                        "path": str(blob_path),
                        "hash": hashlib.sha256(file_response.content).hexdigest()
                    })
    
    def collect_from_local(self, path: str, pattern: str):
        """Collect blobs from local filesystem."""
        import glob
        
        for file_path in glob.glob(os.path.join(path, pattern), recursive=True):
            with open(file_path, "rb") as f:
                content = f.read()
            
            name = Path(file_path).name
            dest = self.output_dir / name
            dest.write_bytes(content)
            
            self.collected.append({
                "source": "local",
                "name": name,
                "path": str(dest),
                "hash": hashlib.sha256(content).hexdigest()
            })
    
    def run(self):
        """Collect from all sources."""
        for source in self.SOURCES:
            print(f"Collecting from {source['name']}...")
            
            if source["type"] == "github":
                self.collect_from_github(
                    source["repo"], 
                    source["path"], 
                    source["pattern"]
                )
            elif source["type"] == "local":
                self.collect_from_local(
                    source["path"],
                    source["pattern"]
                )
        
        print(f"\n✅ Collected {len(self.collected)} blobs")
        return self.collected
```

---

## 6. Automated Training Workflow

### 6.1 Full Automation Pipeline

```python
# automated_training_pipeline.py
"""
Complete automated pipeline for fungal smell training.

Flow:
1. Collect sensor data from specimens
2. Export to AI-Studio format
3. Train model (via Claude Desktop Use or Edge Impulse)
4. Generate BSEC blob
5. Upload to MINDEX
6. Flash to MycoBrain devices
"""

import asyncio
from pathlib import Path
from datetime import datetime

class AutomatedTrainingPipeline:
    """End-to-end smell training automation."""
    
    def __init__(self, config: dict):
        self.config = config
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.data_dir = Path(f"training_sessions/{self.session_id}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_full_pipeline(self, specimens: dict):
        """Run complete training pipeline."""
        
        print("=" * 60)
        print("MINDEX AUTOMATED SMELL TRAINING PIPELINE")
        print(f"Session: {self.session_id}")
        print("=" * 60)
        
        # Step 1: Data Collection
        print("\n[1/5] COLLECTING TRAINING DATA")
        collector = SmellTrainingCollector(port=self.config["serial_port"])
        raw_data = collector.collect_training_session(specimens)
        
        # Step 2: Convert to AI-Studio format
        print("\n[2/5] CONVERTING DATA FORMAT")
        csv_path = self.data_dir / "training_data.csv"
        convert_to_ai_studio_format(str(self.data_dir), str(csv_path))
        
        # Step 3: Train model
        print("\n[3/5] TRAINING MODEL")
        if self.config["training_method"] == "ai_studio":
            await self.train_with_ai_studio(csv_path)
        elif self.config["training_method"] == "edge_impulse":
            await self.train_with_edge_impulse(raw_data)
        else:
            print("   Manual training required - skipping")
        
        # Step 4: Generate blob
        print("\n[4/5] GENERATING BSEC BLOB")
        blob_path = await self.generate_blob()
        
        # Step 5: Upload to MINDEX
        print("\n[5/5] UPLOADING TO MINDEX")
        blob_id = await self.upload_to_mindex(blob_path, specimens)
        
        print("\n" + "=" * 60)
        print("✅ TRAINING COMPLETE")
        print(f"   Blob ID: {blob_id}")
        print(f"   Session: {self.session_id}")
        print("=" * 60)
        
        return blob_id
    
    async def train_with_ai_studio(self, csv_path: Path):
        """Train using Bosch AI-Studio via Claude Desktop Use."""
        automation = AIStudioAutomation()
        
        await automation.import_training_data(str(csv_path))
        await automation.train_model(
            class_labels=list(self.config["specimens"].keys()),
            model_name=f"fungal_{self.session_id}"
        )
    
    async def train_with_edge_impulse(self, raw_data: list):
        """Train using Edge Impulse."""
        trainer = EdgeImpulseTrainer(
            api_key=self.config["edge_impulse_key"],
            project_id=self.config["edge_impulse_project"]
        )
        
        for sample_set in raw_data:
            trainer.upload_samples(sample_set["samples"], sample_set["label"])
        
        job = trainer.train_model()
        print(f"   Training job: {job['id']}")
        
        # Wait for completion
        while True:
            status = trainer.get_job_status(job["id"])
            if status["status"] == "completed":
                break
            await asyncio.sleep(10)
    
    async def generate_blob(self) -> Path:
        """Generate BSEC configuration blob."""
        blob_path = self.data_dir / "bsec_selectivity.config"
        # Blob would be generated by AI-Studio or exported from Edge Impulse
        return blob_path
    
    async def upload_to_mindex(self, blob_path: Path, specimens: dict) -> str:
        """Upload blob to MINDEX registry."""
        import requests
        
        with open(blob_path, "rb") as f:
            response = requests.post(
                f"{self.config['mindex_url']}/api/mindex/blobs",
                files={"blob_file": f},
                data={
                    "name": f"fungal_{self.session_id}",
                    "version": "1.0.0",
                    "class_labels": list(specimens.keys()),
                    "training_samples": sum(
                        s.get("sample_count", 0) for s in specimens.values()
                    )
                }
            )
        
        return response.json()["id"]

# Main execution
if __name__ == "__main__":
    config = {
        "serial_port": "COM7",
        "training_method": "ai_studio",  # or "edge_impulse"
        "mindex_url": "http://localhost:8000",
        "edge_impulse_key": "ei_xxxx",
        "edge_impulse_project": "12345"
    }
    
    specimens = {
        "clean_air": {"duration": 30, "description": "Baseline"},
        "oyster_mushroom": {"duration": 60, "description": "Pleurotus ostreatus fruiting body"},
        "shiitake": {"duration": 60, "description": "Lentinula edodes fruiting body"},
        "contamination": {"duration": 60, "description": "Trichoderma sample"}
    }
    
    pipeline = AutomatedTrainingPipeline(config)
    asyncio.run(pipeline.run_full_pipeline(specimens))
```

---

## 7. Lab Integration Protocol

### 7.1 Physical Setup

```
┌───────────────────────────────────────────────────────────────────┐
│                        SMELL TRAINING LAB                          │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│   ┌─────────────────────┐      ┌─────────────────────┐            │
│   │   Specimen Chamber  │      │   Control Station   │            │
│   │                     │      │                     │            │
│   │  ┌───────────────┐  │      │  ┌───────────────┐  │            │
│   │  │   Fungal      │  │      │  │   Computer    │  │            │
│   │  │   Sample      │  │      │  │   + AI-Studio │  │            │
│   │  └───────────────┘  │      │  └───────────────┘  │            │
│   │         ↓           │      │         ↓           │            │
│   │  ┌───────────────┐  │      │  ┌───────────────┐  │            │
│   │  │   BME688      │──┼──────┼──│   MycoBrain   │  │            │
│   │  │   Sensor      │  │      │  │   Board       │  │            │
│   │  └───────────────┘  │      │  └───────────────┘  │            │
│   │                     │      │                     │            │
│   │   Fan + Airflow     │      │   Serial/USB        │            │
│   └─────────────────────┘      └─────────────────────┘            │
│                                                                    │
│   Reference sensors:                                               │
│   • Ambient temperature probe                                      │
│   • Ambient humidity probe                                         │
│   • Reference gas canister (optional)                              │
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
```

### 7.2 Training Session Protocol

```markdown
## Smell Training Session Protocol

### Pre-Session (Day Before)
- [ ] Ensure BME688 sensors have completed 24-hour burn-in
- [ ] Verify MycoBrain firmware has BSEC2 support
- [ ] Prepare specimen containers (labeled)
- [ ] Check lab ventilation system

### Session Setup
1. Launch MycoBrain Service on computer
2. Open MINDEX training dashboard
3. Verify sensor connections (both BME688s responding)
4. Record baseline conditions:
   - Lab temperature: _____°C
   - Lab humidity: _____%
   - Date/time: __________

### For Each Specimen
1. **Baseline** (30 seconds)
   - Chamber empty, fan running
   - Click "Record Baseline"

2. **Specimen Introduction**
   - Place specimen in chamber
   - Seal chamber
   - Wait 10 seconds for equilibration

3. **Data Collection** (60-120 seconds)
   - Click "Start Recording"
   - Enter specimen label
   - Monitor real-time gas readings
   - Click "Stop Recording" when complete

4. **Specimen Removal**
   - Remove specimen, reseal container
   - Ventilate chamber (30 seconds with fan)

### Post-Session
1. Export all data to CSV
2. Upload to AI-Studio for training
3. Generate BSEC configuration blob
4. Upload blob to MINDEX
5. Test on MycoBrain device
6. Document results in training log
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Create MINDEX database schema for smell registry
- [ ] Build blob storage API
- [ ] Implement data collection scripts
- [ ] Set up lab training station

### Phase 2: Automation (Week 3-4)
- [ ] Integrate Edge Impulse as backup trainer
- [ ] Build Claude Desktop Use scripts for AI-Studio
- [ ] Create automated training pipeline
- [ ] Test with common mushroom species

### Phase 3: Scale (Week 5-8)
- [ ] Deploy community blob aggregator
- [ ] Build researcher contribution portal
- [ ] Train on 50+ fungal species
- [ ] Document all smell signatures

### Phase 4: Production (Week 9-12)
- [ ] Launch MINDEX Smell Registry API
- [ ] Integrate with NatureOS dashboard
- [ ] Publish trained blobs for community
- [ ] Continuous improvement workflow

---

## 9. API Reference

### MINDEX Smell Registry Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/mindex/smells` | List all smell signatures |
| POST | `/api/mindex/smells` | Create smell signature |
| GET | `/api/mindex/blobs` | List all blobs |
| POST | `/api/mindex/blobs` | Upload new blob |
| GET | `/api/mindex/blobs/{id}/download` | Download blob |
| POST | `/api/mindex/training/sessions` | Start training session |
| GET | `/api/mindex/training/sessions/{id}` | Get session status |

---

## 10. Resources & References

- [Bosch BME688 Datasheet](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme688-ds000.pdf)
- [Bosch BME AI-Studio](https://www.bosch-sensortec.com/software/bme/docs/)
- [BSEC2 Library Documentation](https://www.bosch-sensortec.com/software-tools/software/bsec/)
- [PiCockpit BME688 Tutorial](https://picockpit.com/raspberry-pi/teach-bme688-how-to-smell/)
- [Edge Impulse](https://edgeimpulse.com)
- [eNose Project (GitHub)](https://github.com/AndyYuen/eNose)

---

*Document Version: 1.0.0*  
*Last Updated: 2026-01-09*
