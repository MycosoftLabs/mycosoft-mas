#!/usr/bin/env python3
"""
CREP Integration Test Script
Tests all CREP data flows, API endpoints, and MINDEX integration

Run with: python scripts/test_crep_integration.py
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Configuration
WEBSITE_URL = "http://localhost:3010"
MYCOBRAIN_URL = "http://localhost:8765"
MINDEX_URL = "http://localhost:8000"

# Test results
results: List[Dict[str, Any]] = []

def log_test(name: str, passed: bool, details: str = "", response_time_ms: float = 0):
    """Log a test result"""
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name} ({response_time_ms:.0f}ms)")
    if details and not passed:
        print(f"       Details: {details}")
    results.append({
        "name": name,
        "passed": passed,
        "details": details,
        "response_time_ms": response_time_ms,
    })

def test_endpoint(name: str, url: str, method: str = "GET", 
                  payload: Dict = None, expected_status: int = 200,
                  check_fields: List[str] = None) -> Tuple[bool, Dict]:
    """Test an API endpoint"""
    start = time.time()
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=payload, timeout=10)
        
        elapsed = (time.time() - start) * 1000
        
        passed = response.status_code == expected_status
        data = {}
        
        try:
            data = response.json()
        except:
            pass
        
        # Check for required fields
        if passed and check_fields:
            for field in check_fields:
                if field not in data:
                    passed = False
                    break
        
        details = f"Status: {response.status_code}" if not passed else ""
        log_test(name, passed, details, elapsed)
        
        return passed, data
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        log_test(name, False, str(e), elapsed)
        return False, {}

def test_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

# ============================================================
# Test Suite
# ============================================================

def test_mycobrain_service():
    """Test MycoBrain service connectivity"""
    test_section("MycoBrain Service Tests")
    
    test_endpoint("MycoBrain Health", f"{MYCOBRAIN_URL}/health",
                  check_fields=["status"])
    
    test_endpoint("MycoBrain Devices", f"{MYCOBRAIN_URL}/devices",
                  check_fields=["devices"])
    
    test_endpoint("MycoBrain Ports", f"{MYCOBRAIN_URL}/ports",
                  check_fields=["ports"])

def test_device_discovery():
    """Test device discovery API"""
    test_section("Device Discovery Tests")
    
    passed, data = test_endpoint(
        "Discover Devices", 
        f"{WEBSITE_URL}/api/devices/discover",
        check_fields=["devices", "total"]
    )
    
    if passed and data.get("total", 0) > 0:
        print(f"       Found {data['total']} devices, {data.get('online', 0)} online")

def test_device_control():
    """Test device control endpoints"""
    test_section("Device Control Tests")
    
    # Get a connected device
    response = requests.get(f"{WEBSITE_URL}/api/devices/discover", timeout=5)
    devices = response.json().get("devices", [])
    connected = [d for d in devices if d.get("connected")]
    
    if not connected:
        print("  [SKIP] No connected devices found for control tests")
        return
    
    port = connected[0].get("port", "COM7")
    
    # Test control endpoints
    test_endpoint(
        "Control - Beep",
        f"{WEBSITE_URL}/api/mycobrain/{port}/control",
        method="POST",
        payload={"peripheral": "buzzer", "action": "beep", "frequency": 1000, "duration_ms": 100},
        check_fields=["success"]
    )
    
    test_endpoint(
        "Control - LED Rainbow",
        f"{WEBSITE_URL}/api/mycobrain/{port}/control",
        method="POST",
        payload={"peripheral": "neopixel", "action": "rainbow"},
        check_fields=["success"]
    )
    
    time.sleep(1)
    
    test_endpoint(
        "Control - LED Off",
        f"{WEBSITE_URL}/api/mycobrain/{port}/control",
        method="POST",
        payload={"peripheral": "neopixel", "action": "off"},
        check_fields=["success"]
    )

def test_oei_endpoints():
    """Test OEI (Open Earth Intelligence) data endpoints"""
    test_section("OEI Data Endpoint Tests")
    
    test_endpoint(
        "Aircraft (FlightRadar24)",
        f"{WEBSITE_URL}/api/oei/flightradar24",
        check_fields=["aircraft", "total"]
    )
    
    test_endpoint(
        "Vessels (AISStream)",
        f"{WEBSITE_URL}/api/oei/aisstream",
        check_fields=["vessels", "total"]
    )
    
    test_endpoint(
        "Satellites",
        f"{WEBSITE_URL}/api/oei/satellites?category=stations",
        check_fields=["satellites", "total"]
    )
    
    test_endpoint(
        "Global Events",
        f"{WEBSITE_URL}/api/natureos/global-events",
        check_fields=["events"]
    )

def test_mindex_ingestion():
    """Test MINDEX ingestion endpoints"""
    test_section("MINDEX Ingestion Tests")
    
    # Test aircraft ingestion
    test_endpoint(
        "Ingest Aircraft",
        f"{WEBSITE_URL}/api/mindex/ingest/aircraft",
        method="POST",
        payload={
            "source": "test",
            "data": [
                {"id": "TEST001", "icao24": "abc123", "callsign": "TEST001", "latitude": 32.7, "longitude": -117.1}
            ]
        },
        check_fields=["success"]
    )
    
    # Test vessel ingestion
    test_endpoint(
        "Ingest Vessels",
        f"{WEBSITE_URL}/api/mindex/ingest/vessels",
        method="POST",
        payload={
            "source": "test",
            "data": [
                {"id": "VESSEL001", "mmsi": "123456789", "name": "TEST VESSEL", "latitude": 32.7, "longitude": -117.1}
            ]
        },
        check_fields=["success"]
    )
    
    # Test event ingestion
    test_endpoint(
        "Ingest Events",
        f"{WEBSITE_URL}/api/mindex/ingest/events",
        method="POST",
        payload={
            "source": "test",
            "data": [
                {"id": "EVENT001", "type": "earthquake", "title": "Test Event", "latitude": 32.7, "longitude": -117.1}
            ]
        },
        check_fields=["success"]
    )

def test_device_registry():
    """Test device registry API"""
    test_section("Device Registry Tests")
    
    # Get device types
    passed, data = test_endpoint(
        "Get Device Registry",
        f"{WEBSITE_URL}/api/mindex/registry/devices",
        check_fields=["device_types"]
    )
    
    if passed:
        print(f"       Device types: {data.get('device_types', [])}")
    
    # Register a test device
    test_endpoint(
        "Register Device",
        f"{WEBSITE_URL}/api/mindex/registry/devices",
        method="POST",
        payload={
            "id": "test-device-001",
            "type": "mycobrain",
            "name": "Test Device",
            "status": "online"
        },
        check_fields=["success"]
    )

def test_event_registry():
    """Test event registry API"""
    test_section("Event Registry Tests")
    
    # Get event types
    passed, data = test_endpoint(
        "Get Event Registry",
        f"{WEBSITE_URL}/api/mindex/registry/events",
        check_fields=["event_types"]
    )
    
    if passed:
        print(f"       Event types: {len(data.get('event_types', []))} types supported")
    
    # Register a test event
    test_endpoint(
        "Register Event",
        f"{WEBSITE_URL}/api/mindex/registry/events",
        method="POST",
        payload={
            "id": "test-event-001",
            "type": "earthquake",
            "title": "Test Earthquake Event",
            "severity": "low",
            "location": {"lat": 32.7, "lng": -117.1}
        },
        check_fields=["success"]
    )

def test_playback_api():
    """Test playback API"""
    test_section("Playback API Tests")
    
    # Test playback query
    now = datetime.utcnow()
    start = (now - timedelta(hours=1)).isoformat() + "Z"
    end = now.isoformat() + "Z"
    
    test_endpoint(
        "Playback Query",
        f"{WEBSITE_URL}/api/mindex/playback?type=all&start={start}&end={end}",
        check_fields=["type", "frames"]
    )
    
    # Test playback session creation
    test_endpoint(
        "Create Playback Session",
        f"{WEBSITE_URL}/api/mindex/playback",
        method="POST",
        payload={
            "type": "aircraft",
            "start": start,
            "end": end,
            "interval_ms": 60000
        },
        check_fields=["success", "session_id"]
    )

def test_crep_fungal():
    """Test CREP fungal data endpoint"""
    test_section("CREP Fungal Data Tests")
    
    test_endpoint(
        "Fungal Observations",
        f"{WEBSITE_URL}/api/crep/fungal",
        check_fields=["observations"]
    )

def print_summary():
    """Print test summary"""
    test_section("TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    
    print(f"\n  Total Tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Pass Rate: {(passed/total*100):.1f}%")
    
    if failed > 0:
        print(f"\n  Failed Tests:")
        for r in results:
            if not r["passed"]:
                print(f"    - {r['name']}: {r['details']}")
    
    avg_time = sum(r["response_time_ms"] for r in results) / total if total > 0 else 0
    print(f"\n  Average Response Time: {avg_time:.0f}ms")
    
    # Save results to file
    report_path = "crep_integration_test_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed/total*100 if total > 0 else 0,
            "average_response_ms": avg_time,
            "results": results
        }, f, indent=2)
    print(f"\n  Report saved to: {report_path}")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print(" CREP INTEGRATION TEST SUITE")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Run test suites
    test_mycobrain_service()
    test_device_discovery()
    test_device_control()
    test_oei_endpoints()
    test_mindex_ingestion()
    test_device_registry()
    test_event_registry()
    test_playback_api()
    test_crep_fungal()
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main()
