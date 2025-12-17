#!/usr/bin/env python3
"""
UART Ingest Agent for MycoBrain
Reads serial data from MycoBrain hardware and writes structured logs
"""

import os
import sys
import json
import time
import serial
from datetime import datetime
from pythonjsonlogger import jsonlogger

# Configuration
UART_DEVICE = os.getenv("UART_DEVICE", "/dev/ttyUSB0")
UART_BAUD = int(os.getenv("UART_BAUD", "115200"))
LOG_DIR = os.getenv("LOG_DIR", "/logs")
LOG_FILE = os.path.join(LOG_DIR, "uart_ingest.jsonl")

# Setup logging
logger_handler = open(LOG_FILE, "a")
json_handler = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(message)s %(data)s'
)


class MycoBrainUARTAgent:
    """UART ingest agent for MycoBrain"""
    
    def __init__(self, device: str, baudrate: int):
        self.device = device
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        
    def connect(self):
        """Connect to UART device"""
        try:
            self.serial = serial.Serial(
                self.device,
                self.baudrate,
                timeout=1
            )
            print(f"Connected to {self.device} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to {self.device}: {e}", file=sys.stderr)
            return False
    
    def parse_frame(self, raw_data: bytes) -> dict:
        """
        Parse raw UART frame into structured data
        
        Expected format (example):
        - Text lines: human-readable status
        - JSON lines: structured sensor data
        """
        try:
            # Try to decode as text
            text = raw_data.decode('utf-8', errors='ignore').strip()
            
            if not text:
                return None
            
            # Try to parse as JSON first
            try:
                data = json.loads(text)
                return {
                    "type": "json",
                    "data": data
                }
            except json.JSONDecodeError:
                # Plain text
                return {
                    "type": "text",
                    "data": text
                }
        except Exception as e:
            return {
                "type": "error",
                "error": str(e),
                "raw": raw_data.hex()
            }
    
    def log_event(self, event_type: str, data: dict):
        """Write event to JSON log"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "INFO",
            "message": f"UART event: {event_type}",
            "data": data
        }
        logger_handler.write(json.dumps(log_entry) + "\n")
        logger_handler.flush()
    
    def run(self):
        """Main ingest loop"""
        self.running = True
        
        print(f"Starting UART ingest from {self.device}")
        
        while self.running:
            try:
                if not self.serial or not self.serial.is_open:
                    if not self.connect():
                        time.sleep(5)
                        continue
                
                # Read line from serial
                if self.serial.in_waiting > 0:
                    line = self.serial.readline()
                    
                    if line:
                        # Parse frame
                        frame = self.parse_frame(line)
                        
                        if frame:
                            # Log event
                            self.log_event(frame["type"], frame)
                            
                            # Print to stdout for docker logs
                            print(json.dumps({
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "frame": frame
                            }))
                
                time.sleep(0.01)  # Small delay to prevent CPU spin
                
            except serial.SerialException as e:
                print(f"Serial error: {e}", file=sys.stderr)
                self.serial = None
                time.sleep(5)
            except KeyboardInterrupt:
                print("Shutting down...")
                self.running = False
            except Exception as e:
                print(f"Unexpected error: {e}", file=sys.stderr)
                time.sleep(1)
        
        if self.serial:
            self.serial.close()


def main():
    """Entry point"""
    agent = MycoBrainUARTAgent(UART_DEVICE, UART_BAUD)
    
    # Log startup
    print(json.dumps({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "INFO",
        "message": "UART agent starting",
        "data": {
            "device": UART_DEVICE,
            "baudrate": UART_BAUD,
            "log_file": LOG_FILE
        }
    }))
    
    agent.run()


if __name__ == "__main__":
    main()
