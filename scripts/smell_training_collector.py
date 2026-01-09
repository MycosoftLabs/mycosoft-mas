#!/usr/bin/env python3
"""
MINDEX Smell Training Data Collector

Automated data collection from BME688 sensors for smell training.
Part of the MINDEX Automated Smell Training System.

Usage:
    python smell_training_collector.py --port COM7 --specimens specimens.json
    python smell_training_collector.py --port COM7 --interactive
"""

import serial
import json
import time
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class SmellTrainingCollector:
    """Automated smell training data collection for BME688."""
    
    def __init__(self, port: str = "COM7", baud: int = 115200):
        self.port = port
        self.baud = baud
        self.serial: Optional[serial.Serial] = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.data_dir = Path(f"training_data/{self.session_id}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metadata: Dict[str, Any] = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "port": port,
            "specimens": [],
            "total_samples": 0
        }
        
    def connect(self) -> bool:
        """Connect to MycoBrain board."""
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(0.5)  # Wait for connection
            print(f"✅ Connected to {self.port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from board."""
        if self.serial:
            self.serial.close()
            self.serial = None
    
    def send_command(self, cmd: str) -> str:
        """Send command and get response."""
        if not self.serial:
            return ""
        
        self.serial.write(f"{cmd}\n".encode())
        time.sleep(0.3)
        response = self.serial.read_all().decode(errors="ignore")
        return response
    
    def get_sensor_data(self) -> Optional[Dict[str, Any]]:
        """Get current sensor readings."""
        response = self.send_command("sensors")
        
        for line in response.split("\n"):
            if line.startswith("{") and ('"bme1"' in line or '"ok"' in line):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    pass
        return None
    
    def verify_sensors(self) -> Dict[str, bool]:
        """Verify BME688 sensors are connected."""
        data = self.get_sensor_data()
        
        result = {
            "bme688_0x77": False,
            "bme688_0x76": False
        }
        
        if data:
            if "bme1" in data and data["bme1"].get("temp_c"):
                result["bme688_0x77"] = True
            if "bme2" in data and data["bme2"].get("temp_c"):
                result["bme688_0x76"] = True
        
        return result
    
    def collect_sample(
        self, 
        label: str, 
        duration_sec: int = 60, 
        interval_sec: float = 1.0,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Collect training samples for a specific smell class.
        
        Args:
            label: Class label (e.g., "oyster_mushroom", "trichoderma")
            duration_sec: How long to collect (seconds)
            interval_sec: Time between samples
            description: Optional description of specimen
        
        Returns:
            Collection result metadata
        """
        samples: List[Dict[str, Any]] = []
        start_time = time.time()
        sample_count = 0
        
        print(f"\n📊 Collecting samples for '{label}'")
        print(f"   Duration: {duration_sec}s | Interval: {interval_sec}s")
        if description:
            print(f"   Description: {description}")
        print("   Progress: ", end="", flush=True)
        
        while time.time() - start_time < duration_sec:
            data = self.get_sensor_data()
            
            if data:
                sample = {
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_sec": round(time.time() - start_time, 2),
                    "label": label,
                    "bme1": data.get("bme1", {}),
                    "bme2": data.get("bme2", {}),
                    "bme688_count": data.get("bme688_count", 0)
                }
                
                # Add BSEC2 data if available
                if "iaq" in data.get("bme1", {}):
                    sample["has_bsec2"] = True
                
                samples.append(sample)
                sample_count += 1
                
                # Progress indicator
                if sample_count % 10 == 0:
                    print(".", end="", flush=True)
            
            time.sleep(interval_sec)
        
        print(f" Done! ({sample_count} samples)")
        
        # Save to file
        safe_label = label.replace(" ", "_").replace("/", "-")
        output_file = self.data_dir / f"{safe_label}_{sample_count}_samples.json"
        
        with open(output_file, "w") as f:
            json.dump({
                "label": label,
                "description": description,
                "duration_sec": duration_sec,
                "interval_sec": interval_sec,
                "sample_count": sample_count,
                "collected_at": datetime.now().isoformat(),
                "samples": samples
            }, f, indent=2)
        
        print(f"   💾 Saved to: {output_file}")
        
        # Update metadata
        self.metadata["specimens"].append({
            "label": label,
            "description": description,
            "sample_count": sample_count,
            "file": str(output_file)
        })
        self.metadata["total_samples"] += sample_count
        
        return {
            "label": label,
            "count": sample_count,
            "file": str(output_file),
            "samples": samples
        }
    
    def collect_baseline(self, duration_sec: int = 30) -> Dict[str, Any]:
        """Collect clean air baseline."""
        print("\n🌬️ COLLECTING BASELINE (Clean Air)")
        print("   Ensure chamber is empty and ventilated...")
        input("   Press ENTER when ready...")
        
        return self.collect_sample(
            label="clean_air_baseline",
            duration_sec=duration_sec,
            description="Clean ambient air for reference baseline"
        )
    
    def collect_training_session(self, specimens: Dict[str, Dict]) -> List[Dict]:
        """
        Collect a full training session with multiple specimens.
        
        Args:
            specimens: Dict of {label: {"duration": int, "description": str}}
        
        Returns:
            List of collection results
        """
        results = []
        
        print("\n" + "=" * 60)
        print("MINDEX SMELL TRAINING SESSION")
        print(f"Session ID: {self.session_id}")
        print(f"Specimens: {len(specimens)}")
        print("=" * 60)
        
        # Connect to board
        if not self.connect():
            return []
        
        # Verify sensors
        sensors = self.verify_sensors()
        print(f"\n🔍 Sensor Status:")
        print(f"   BME688 @ 0x77: {'✅ Connected' if sensors['bme688_0x77'] else '❌ Not found'}")
        print(f"   BME688 @ 0x76: {'✅ Connected' if sensors['bme688_0x76'] else '❌ Not found'}")
        
        if not any(sensors.values()):
            print("❌ No BME688 sensors found. Aborting.")
            return []
        
        # Collect baseline first
        baseline = self.collect_baseline()
        results.append(baseline)
        
        # Collect each specimen
        for i, (label, config) in enumerate(specimens.items(), 1):
            print(f"\n{'='*60}")
            print(f"SPECIMEN {i}/{len(specimens)}: {label}")
            print(f"{'='*60}")
            
            print(f"\n🍄 Place specimen: {label}")
            if config.get("description"):
                print(f"   Description: {config['description']}")
            print("   Seal chamber and wait for equilibration...")
            input("   Press ENTER when ready to start recording...")
            
            result = self.collect_sample(
                label=label,
                duration_sec=config.get("duration", 60),
                interval_sec=config.get("interval", 1.0),
                description=config.get("description", "")
            )
            results.append(result)
            
            print("\n   Remove specimen and ventilate chamber...")
            print("   Waiting 15 seconds for air to clear...")
            time.sleep(15)
        
        # Save session metadata
        self.metadata["end_time"] = datetime.now().isoformat()
        self.metadata["results"] = [
            {"label": r["label"], "count": r["count"], "file": r["file"]}
            for r in results
        ]
        
        metadata_file = self.data_dir / "session_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)
        
        print(f"\n📦 Session metadata saved to: {metadata_file}")
        
        # Disconnect
        self.disconnect()
        
        return results
    
    def interactive_session(self):
        """Run interactive training session."""
        print("\n" + "=" * 60)
        print("MINDEX INTERACTIVE SMELL TRAINING")
        print("=" * 60)
        
        if not self.connect():
            return
        
        specimens = {}
        
        print("\nEnter specimens to train (type 'done' when finished):\n")
        
        while True:
            label = input("Specimen label (or 'done'): ").strip()
            if label.lower() == "done":
                break
            if not label:
                continue
            
            description = input("  Description: ").strip()
            duration = input("  Duration (seconds, default 60): ").strip()
            
            specimens[label] = {
                "description": description,
                "duration": int(duration) if duration else 60
            }
            
            print(f"  ✅ Added: {label}\n")
        
        if not specimens:
            print("No specimens entered. Exiting.")
            return
        
        print(f"\n📋 Training plan: {len(specimens)} specimens")
        for label, config in specimens.items():
            print(f"   • {label}: {config['duration']}s - {config['description']}")
        
        confirm = input("\nStart training session? (y/n): ").strip().lower()
        if confirm == "y":
            self.collect_training_session(specimens)


def convert_to_csv(training_dir: str, output_file: str):
    """Convert collected JSON data to AI-Studio compatible CSV."""
    import csv
    
    training_path = Path(training_dir)
    all_samples = []
    
    # Load all sample files
    for json_file in training_path.glob("*_samples.json"):
        with open(json_file) as f:
            data = json.load(f)
            for sample in data.get("samples", []):
                sample["label"] = data["label"]
                all_samples.append(sample)
    
    if not all_samples:
        print("No samples found!")
        return
    
    # Write CSV
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "timestamp", "class_label",
            "gas_resistance_amb", "temp_amb", "humidity_amb", "pressure_amb",
            "iaq_amb", "co2eq_amb", "bvoc_amb",
            "gas_resistance_env", "temp_env", "humidity_env", "pressure_env",
            "iaq_env", "co2eq_env", "bvoc_env"
        ])
        
        # Data rows
        for sample in all_samples:
            bme1 = sample.get("bme1", {})
            bme2 = sample.get("bme2", {})
            
            writer.writerow([
                sample.get("timestamp", ""),
                sample.get("label", ""),
                bme1.get("gas_ohm", ""),
                bme1.get("temp_c", ""),
                bme1.get("rh_pct", ""),
                bme1.get("press_hpa", ""),
                bme1.get("iaq", ""),
                bme1.get("co2_equivalent", ""),
                bme1.get("voc_equivalent", ""),
                bme2.get("gas_ohm", ""),
                bme2.get("temp_c", ""),
                bme2.get("rh_pct", ""),
                bme2.get("press_hpa", ""),
                bme2.get("iaq", ""),
                bme2.get("co2_equivalent", ""),
                bme2.get("voc_equivalent", "")
            ])
    
    print(f"✅ Exported {len(all_samples)} samples to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="MINDEX Smell Training Data Collector"
    )
    parser.add_argument(
        "--port", "-p", 
        default="COM7", 
        help="Serial port (default: COM7)"
    )
    parser.add_argument(
        "--specimens", "-s", 
        help="JSON file with specimen definitions"
    )
    parser.add_argument(
        "--interactive", "-i", 
        action="store_true",
        help="Run interactive mode"
    )
    parser.add_argument(
        "--convert", "-c", 
        help="Convert training directory to CSV"
    )
    parser.add_argument(
        "--output", "-o", 
        default="training_data.csv",
        help="Output CSV file (with --convert)"
    )
    
    args = parser.parse_args()
    
    # Convert mode
    if args.convert:
        convert_to_csv(args.convert, args.output)
        return
    
    # Interactive mode
    if args.interactive:
        collector = SmellTrainingCollector(port=args.port)
        collector.interactive_session()
        return
    
    # File-based mode
    if args.specimens:
        with open(args.specimens) as f:
            specimens = json.load(f)
        
        collector = SmellTrainingCollector(port=args.port)
        results = collector.collect_training_session(specimens)
        
        print(f"\n{'='*60}")
        print("SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"Total specimens: {len(results)}")
        print(f"Total samples: {sum(r['count'] for r in results)}")
        print(f"Data directory: {collector.data_dir}")
        return
    
    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
