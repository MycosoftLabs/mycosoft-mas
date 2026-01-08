"""Test MycoBrain commands via API"""
import requests
import time

BASE = "http://localhost:8003"

def test_command(name, cmd):
    print(f"\n{name}...")
    try:
        r = requests.post(f"{BASE}/devices/mycobrain-COM5/command", json={"command": cmd}, timeout=5)
        print(f"  Status: {r.status_code}")
        print(f"  Response: {r.text[:300]}")
    except Exception as e:
        print(f"  Error: {e}")

print("=== MYCOBRAIN COM5 (Side A) TESTS ===")

# Check connection
print("\nDevice status:")
r = requests.get(f"{BASE}/devices")
print(f"  {r.json()}")

# Run tests
test_command("1. Status", {"cmd": "status"})
time.sleep(0.5)

test_command("2. LED Red", {"cmd": "led", "r": 255, "g": 0, "b": 0})
time.sleep(0.5)

test_command("3. LED Green", {"cmd": "led", "r": 0, "g": 255, "b": 0})
time.sleep(0.5)

test_command("4. LED Blue", {"cmd": "led", "r": 0, "g": 0, "b": 255})
time.sleep(0.5)

test_command("5. LED Off", {"cmd": "led", "r": 0, "g": 0, "b": 0})
time.sleep(0.5)

test_command("6. Buzzer Beep", {"cmd": "buzzer", "freq": 1000, "dur": 200})
time.sleep(0.5)

test_command("7. Buzzer Melody", {"cmd": "melody", "name": "coin"})
time.sleep(0.5)

test_command("8. Ping", {"cmd": "ping"})
time.sleep(0.5)

test_command("9. Sensors", {"cmd": "sensors"})
time.sleep(0.5)

test_command("10. I2C Scan", {"cmd": "i2c_scan"})

print("\n=== TESTS COMPLETE ===")
