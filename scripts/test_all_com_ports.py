#!/usr/bin/env python3
"""Test all COM ports for MycoBrain devices"""
import requests
import time
import sys

SERVICE_URL = "http://localhost:8003"
PORTS = ["COM3", "COM4", "COM6"]

print("\n" + "="*60)
print("MycoBrain COM Port Test")
print("="*60 + "\n")

# Check service
try:
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    if r.status_code != 200:
        print("Service not running!")
        sys.exit(1)
    print("Service: OK\n")
except Exception as e:
    print(f"Service not accessible: {e}")
    sys.exit(1)

# Test each port
connected = []
for port in PORTS:
    print(f"Testing {port}...")
    try:
        r = requests.post(
            f"{SERVICE_URL}/devices/connect/{port}",
            json={"port": port, "baudrate": 115200},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            device_id = data.get("device_id")
            status = data.get("status")
            print(f"  OK - Connected: {device_id} (Status: {status})")
            connected.append((port, device_id))
        else:
            error = r.json().get("detail", "Unknown error")
            print(f"  FAIL - {error}")
    except Exception as e:
        print(f"  ERROR - {e}")
    time.sleep(1)

print(f"\n{'='*60}")
print(f"Results: {len(connected)} device(s) connected")
if connected:
    for port, dev_id in connected:
        print(f"  - {port}: {dev_id}")
print("="*60 + "\n")

if len(connected) > 0:
    sys.exit(0)
else:
    sys.exit(1)







#!/usr/bin/env python3
"""Test all COM ports for MycoBrain devices"""
import requests
import time
import sys

SERVICE_URL = "http://localhost:8003"
PORTS = ["COM3", "COM4", "COM6"]

print("\n" + "="*60)
print("MycoBrain COM Port Test")
print("="*60 + "\n")

# Check service
try:
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    if r.status_code != 200:
        print("Service not running!")
        sys.exit(1)
    print("Service: OK\n")
except Exception as e:
    print(f"Service not accessible: {e}")
    sys.exit(1)

# Test each port
connected = []
for port in PORTS:
    print(f"Testing {port}...")
    try:
        r = requests.post(
            f"{SERVICE_URL}/devices/connect/{port}",
            json={"port": port, "baudrate": 115200},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            device_id = data.get("device_id")
            status = data.get("status")
            print(f"  OK - Connected: {device_id} (Status: {status})")
            connected.append((port, device_id))
        else:
            error = r.json().get("detail", "Unknown error")
            print(f"  FAIL - {error}")
    except Exception as e:
        print(f"  ERROR - {e}")
    time.sleep(1)

print(f"\n{'='*60}")
print(f"Results: {len(connected)} device(s) connected")
if connected:
    for port, dev_id in connected:
        print(f"  - {port}: {dev_id}")
print("="*60 + "\n")

if len(connected) > 0:
    sys.exit(0)
else:
    sys.exit(1)








#!/usr/bin/env python3
"""Test all COM ports for MycoBrain devices"""
import requests
import time
import sys

SERVICE_URL = "http://localhost:8003"
PORTS = ["COM3", "COM4", "COM6"]

print("\n" + "="*60)
print("MycoBrain COM Port Test")
print("="*60 + "\n")

# Check service
try:
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    if r.status_code != 200:
        print("Service not running!")
        sys.exit(1)
    print("Service: OK\n")
except Exception as e:
    print(f"Service not accessible: {e}")
    sys.exit(1)

# Test each port
connected = []
for port in PORTS:
    print(f"Testing {port}...")
    try:
        r = requests.post(
            f"{SERVICE_URL}/devices/connect/{port}",
            json={"port": port, "baudrate": 115200},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            device_id = data.get("device_id")
            status = data.get("status")
            print(f"  OK - Connected: {device_id} (Status: {status})")
            connected.append((port, device_id))
        else:
            error = r.json().get("detail", "Unknown error")
            print(f"  FAIL - {error}")
    except Exception as e:
        print(f"  ERROR - {e}")
    time.sleep(1)

print(f"\n{'='*60}")
print(f"Results: {len(connected)} device(s) connected")
if connected:
    for port, dev_id in connected:
        print(f"  - {port}: {dev_id}")
print("="*60 + "\n")

if len(connected) > 0:
    sys.exit(0)
else:
    sys.exit(1)







#!/usr/bin/env python3
"""Test all COM ports for MycoBrain devices"""
import requests
import time
import sys

SERVICE_URL = "http://localhost:8003"
PORTS = ["COM3", "COM4", "COM6"]

print("\n" + "="*60)
print("MycoBrain COM Port Test")
print("="*60 + "\n")

# Check service
try:
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    if r.status_code != 200:
        print("Service not running!")
        sys.exit(1)
    print("Service: OK\n")
except Exception as e:
    print(f"Service not accessible: {e}")
    sys.exit(1)

# Test each port
connected = []
for port in PORTS:
    print(f"Testing {port}...")
    try:
        r = requests.post(
            f"{SERVICE_URL}/devices/connect/{port}",
            json={"port": port, "baudrate": 115200},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            device_id = data.get("device_id")
            status = data.get("status")
            print(f"  OK - Connected: {device_id} (Status: {status})")
            connected.append((port, device_id))
        else:
            error = r.json().get("detail", "Unknown error")
            print(f"  FAIL - {error}")
    except Exception as e:
        print(f"  ERROR - {e}")
    time.sleep(1)

print(f"\n{'='*60}")
print(f"Results: {len(connected)} device(s) connected")
if connected:
    for port, dev_id in connected:
        print(f"  - {port}: {dev_id}")
print("="*60 + "\n")

if len(connected) > 0:
    sys.exit(0)
else:
    sys.exit(1)











#!/usr/bin/env python3
"""Test all COM ports for MycoBrain devices"""
import requests
import time
import sys

SERVICE_URL = "http://localhost:8003"
PORTS = ["COM3", "COM4", "COM6"]

print("\n" + "="*60)
print("MycoBrain COM Port Test")
print("="*60 + "\n")

# Check service
try:
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    if r.status_code != 200:
        print("Service not running!")
        sys.exit(1)
    print("Service: OK\n")
except Exception as e:
    print(f"Service not accessible: {e}")
    sys.exit(1)

# Test each port
connected = []
for port in PORTS:
    print(f"Testing {port}...")
    try:
        r = requests.post(
            f"{SERVICE_URL}/devices/connect/{port}",
            json={"port": port, "baudrate": 115200},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            device_id = data.get("device_id")
            status = data.get("status")
            print(f"  OK - Connected: {device_id} (Status: {status})")
            connected.append((port, device_id))
        else:
            error = r.json().get("detail", "Unknown error")
            print(f"  FAIL - {error}")
    except Exception as e:
        print(f"  ERROR - {e}")
    time.sleep(1)

print(f"\n{'='*60}")
print(f"Results: {len(connected)} device(s) connected")
if connected:
    for port, dev_id in connected:
        print(f"  - {port}: {dev_id}")
print("="*60 + "\n")

if len(connected) > 0:
    sys.exit(0)
else:
    sys.exit(1)







#!/usr/bin/env python3
"""Test all COM ports for MycoBrain devices"""
import requests
import time
import sys

SERVICE_URL = "http://localhost:8003"
PORTS = ["COM3", "COM4", "COM6"]

print("\n" + "="*60)
print("MycoBrain COM Port Test")
print("="*60 + "\n")

# Check service
try:
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    if r.status_code != 200:
        print("Service not running!")
        sys.exit(1)
    print("Service: OK\n")
except Exception as e:
    print(f"Service not accessible: {e}")
    sys.exit(1)

# Test each port
connected = []
for port in PORTS:
    print(f"Testing {port}...")
    try:
        r = requests.post(
            f"{SERVICE_URL}/devices/connect/{port}",
            json={"port": port, "baudrate": 115200},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            device_id = data.get("device_id")
            status = data.get("status")
            print(f"  OK - Connected: {device_id} (Status: {status})")
            connected.append((port, device_id))
        else:
            error = r.json().get("detail", "Unknown error")
            print(f"  FAIL - {error}")
    except Exception as e:
        print(f"  ERROR - {e}")
    time.sleep(1)

print(f"\n{'='*60}")
print(f"Results: {len(connected)} device(s) connected")
if connected:
    for port, dev_id in connected:
        print(f"  - {port}: {dev_id}")
print("="*60 + "\n")

if len(connected) > 0:
    sys.exit(0)
else:
    sys.exit(1)








#!/usr/bin/env python3
"""Test all COM ports for MycoBrain devices"""
import requests
import time
import sys

SERVICE_URL = "http://localhost:8003"
PORTS = ["COM3", "COM4", "COM6"]

print("\n" + "="*60)
print("MycoBrain COM Port Test")
print("="*60 + "\n")

# Check service
try:
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    if r.status_code != 200:
        print("Service not running!")
        sys.exit(1)
    print("Service: OK\n")
except Exception as e:
    print(f"Service not accessible: {e}")
    sys.exit(1)

# Test each port
connected = []
for port in PORTS:
    print(f"Testing {port}...")
    try:
        r = requests.post(
            f"{SERVICE_URL}/devices/connect/{port}",
            json={"port": port, "baudrate": 115200},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            device_id = data.get("device_id")
            status = data.get("status")
            print(f"  OK - Connected: {device_id} (Status: {status})")
            connected.append((port, device_id))
        else:
            error = r.json().get("detail", "Unknown error")
            print(f"  FAIL - {error}")
    except Exception as e:
        print(f"  ERROR - {e}")
    time.sleep(1)

print(f"\n{'='*60}")
print(f"Results: {len(connected)} device(s) connected")
if connected:
    for port, dev_id in connected:
        print(f"  - {port}: {dev_id}")
print("="*60 + "\n")

if len(connected) > 0:
    sys.exit(0)
else:
    sys.exit(1)







#!/usr/bin/env python3
"""Test all COM ports for MycoBrain devices"""
import requests
import time
import sys

SERVICE_URL = "http://localhost:8003"
PORTS = ["COM3", "COM4", "COM6"]

print("\n" + "="*60)
print("MycoBrain COM Port Test")
print("="*60 + "\n")

# Check service
try:
    r = requests.get(f"{SERVICE_URL}/health", timeout=5)
    if r.status_code != 200:
        print("Service not running!")
        sys.exit(1)
    print("Service: OK\n")
except Exception as e:
    print(f"Service not accessible: {e}")
    sys.exit(1)

# Test each port
connected = []
for port in PORTS:
    print(f"Testing {port}...")
    try:
        r = requests.post(
            f"{SERVICE_URL}/devices/connect/{port}",
            json={"port": port, "baudrate": 115200},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            device_id = data.get("device_id")
            status = data.get("status")
            print(f"  OK - Connected: {device_id} (Status: {status})")
            connected.append((port, device_id))
        else:
            error = r.json().get("detail", "Unknown error")
            print(f"  FAIL - {error}")
    except Exception as e:
        print(f"  ERROR - {e}")
    time.sleep(1)

print(f"\n{'='*60}")
print(f"Results: {len(connected)} device(s) connected")
if connected:
    for port, dev_id in connected:
        print(f"  - {port}: {dev_id}")
print("="*60 + "\n")

if len(connected) > 0:
    sys.exit(0)
else:
    sys.exit(1)











