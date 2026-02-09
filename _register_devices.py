"""
Register all MycoBrain devices in the MINDEX PostgreSQL database.
Created: February 5, 2026
"""
import paramiko
import os
import json

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = os.getenv("SANDBOX_PASSWORD", "REDACTED_VM_SSH_PASSWORD")

# Device definitions with comprehensive metadata
devices = [
    # Core Devices
    {
        "name": "SporeBase-001",
        "device_type": "controller",
        "location": "Lab Rack 1",
        "description": "SporeBase Primary Controller - ESP32-S3 with 7-inch touchscreen",
        "mac_address": "00:1A:2B:3C:4D:01",
        "ip_address": "192.168.0.150",
        "firmware_version": "2.1.0",
        "status": "active",
        "capabilities": ["touchscreen", "wifi", "bluetooth", "mqtt", "nfc"],
        "sensors": ["temperature", "humidity", "co2", "light"]
    },
    {
        "name": "Mushroom1-Main",
        "device_type": "controller",
        "location": "Grow Chamber 1",
        "description": "Mushroom1 Main Control Unit - Full environmental control",
        "mac_address": "00:1A:2B:3C:4D:02",
        "ip_address": "192.168.0.151",
        "firmware_version": "2.0.5",
        "status": "active",
        "capabilities": ["wifi", "mqtt", "modbus", "relay_control"],
        "sensors": ["temperature", "humidity", "co2", "weight"]
    },
    
    # Environmental Sensors
    {
        "name": "TempHumid-Sensor-01",
        "device_type": "sensor",
        "location": "Grow Chamber 1 - Top",
        "description": "SHT40 Temperature and Humidity Sensor",
        "mac_address": "00:1A:2B:3C:4D:10",
        "ip_address": None,
        "firmware_version": "1.2.0",
        "status": "active",
        "capabilities": ["i2c"],
        "sensors": ["temperature", "humidity"]
    },
    {
        "name": "TempHumid-Sensor-02",
        "device_type": "sensor",
        "location": "Grow Chamber 1 - Bottom",
        "description": "SHT40 Temperature and Humidity Sensor",
        "mac_address": "00:1A:2B:3C:4D:11",
        "ip_address": None,
        "firmware_version": "1.2.0",
        "status": "active",
        "capabilities": ["i2c"],
        "sensors": ["temperature", "humidity"]
    },
    {
        "name": "CO2-Sensor-01",
        "device_type": "sensor",
        "location": "Grow Chamber 1",
        "description": "SCD41 CO2 Sensor with Temperature and Humidity",
        "mac_address": "00:1A:2B:3C:4D:20",
        "ip_address": None,
        "firmware_version": "1.3.1",
        "status": "active",
        "capabilities": ["i2c"],
        "sensors": ["co2", "temperature", "humidity"]
    },
    {
        "name": "CO2-Sensor-02",
        "device_type": "sensor",
        "location": "Fruiting Chamber",
        "description": "SCD41 CO2 Sensor",
        "mac_address": "00:1A:2B:3C:4D:21",
        "ip_address": None,
        "firmware_version": "1.3.1",
        "status": "active",
        "capabilities": ["i2c"],
        "sensors": ["co2", "temperature", "humidity"]
    },
    
    # Light Sensors
    {
        "name": "Light-Sensor-01",
        "device_type": "sensor",
        "location": "Grow Chamber 1 - Canopy Level",
        "description": "TSL2591 High Dynamic Range Light Sensor",
        "mac_address": "00:1A:2B:3C:4D:30",
        "ip_address": None,
        "firmware_version": "1.0.2",
        "status": "active",
        "capabilities": ["i2c"],
        "sensors": ["lux", "full_spectrum", "infrared"]
    },
    {
        "name": "Light-Sensor-02",
        "device_type": "sensor",
        "location": "Fruiting Chamber",
        "description": "TSL2591 Light Sensor",
        "mac_address": "00:1A:2B:3C:4D:31",
        "ip_address": None,
        "firmware_version": "1.0.2",
        "status": "active",
        "capabilities": ["i2c"],
        "sensors": ["lux", "full_spectrum", "infrared"]
    },
    
    # Weight/Scale Sensors
    {
        "name": "Scale-Sensor-01",
        "device_type": "sensor",
        "location": "Grow Chamber 1 - Tray 1",
        "description": "HX711 Load Cell - 5kg capacity",
        "mac_address": "00:1A:2B:3C:4D:40",
        "ip_address": None,
        "firmware_version": "1.1.0",
        "status": "active",
        "capabilities": ["gpio"],
        "sensors": ["weight"]
    },
    {
        "name": "Scale-Sensor-02",
        "device_type": "sensor",
        "location": "Grow Chamber 1 - Tray 2",
        "description": "HX711 Load Cell - 5kg capacity",
        "mac_address": "00:1A:2B:3C:4D:41",
        "ip_address": None,
        "firmware_version": "1.1.0",
        "status": "active",
        "capabilities": ["gpio"],
        "sensors": ["weight"]
    },
    
    # Cameras
    {
        "name": "Camera-ESP32-01",
        "device_type": "camera",
        "location": "Grow Chamber 1 - Overview",
        "description": "ESP32-CAM OV2640 with IR capability",
        "mac_address": "00:1A:2B:3C:4D:50",
        "ip_address": "192.168.0.160",
        "firmware_version": "1.5.0",
        "status": "active",
        "capabilities": ["wifi", "http_stream", "motion_detect", "ir"],
        "sensors": ["image", "motion"]
    },
    {
        "name": "Camera-ESP32-02",
        "device_type": "camera",
        "location": "Fruiting Chamber - Close-up",
        "description": "ESP32-CAM OV2640 with Macro Lens",
        "mac_address": "00:1A:2B:3C:4D:51",
        "ip_address": "192.168.0.161",
        "firmware_version": "1.5.0",
        "status": "active",
        "capabilities": ["wifi", "http_stream", "timelapse"],
        "sensors": ["image"]
    },
    
    # Actuators - Relay Modules
    {
        "name": "Relay-Module-01",
        "device_type": "actuator",
        "location": "Grow Chamber 1 - Control Panel",
        "description": "8-Channel Relay Module for environmental control",
        "mac_address": "00:1A:2B:3C:4D:60",
        "ip_address": None,
        "firmware_version": "1.0.0",
        "status": "active",
        "capabilities": ["gpio", "8_channel"],
        "sensors": []
    },
    {
        "name": "Humidifier-Controller-01",
        "device_type": "actuator",
        "location": "Grow Chamber 1",
        "description": "Ultrasonic Humidifier with PWM control",
        "mac_address": "00:1A:2B:3C:4D:70",
        "ip_address": None,
        "firmware_version": "1.2.0",
        "status": "active",
        "capabilities": ["pwm", "relay"],
        "sensors": []
    },
    {
        "name": "Fan-Controller-01",
        "device_type": "actuator",
        "location": "Grow Chamber 1 - Intake",
        "description": "PWM Fan Controller for ventilation",
        "mac_address": "00:1A:2B:3C:4D:71",
        "ip_address": None,
        "firmware_version": "1.1.0",
        "status": "active",
        "capabilities": ["pwm"],
        "sensors": ["rpm"]
    },
    {
        "name": "Fan-Controller-02",
        "device_type": "actuator",
        "location": "Grow Chamber 1 - Exhaust",
        "description": "PWM Fan Controller for ventilation",
        "mac_address": "00:1A:2B:3C:4D:72",
        "ip_address": None,
        "firmware_version": "1.1.0",
        "status": "active",
        "capabilities": ["pwm"],
        "sensors": ["rpm"]
    },
    
    # LED Controllers
    {
        "name": "LED-Controller-01",
        "device_type": "actuator",
        "location": "Grow Chamber 1 - Canopy",
        "description": "RGB+W LED Controller with spectrum control",
        "mac_address": "00:1A:2B:3C:4D:80",
        "ip_address": "192.168.0.170",
        "firmware_version": "2.0.0",
        "status": "active",
        "capabilities": ["wifi", "dmx", "spectrum_control"],
        "sensors": []
    },
    
    # NFC Readers
    {
        "name": "NFC-Reader-01",
        "device_type": "interface",
        "location": "SporeBase-001",
        "description": "PN532 NFC Reader for substrate tagging",
        "mac_address": "00:1A:2B:3C:4D:90",
        "ip_address": None,
        "firmware_version": "1.0.5",
        "status": "active",
        "capabilities": ["spi", "nfc_read", "nfc_write"],
        "sensors": []
    },
    
    # pH/EC Sensors
    {
        "name": "pH-Sensor-01",
        "device_type": "sensor",
        "location": "Nutrient Reservoir",
        "description": "Analog pH Sensor with calibration",
        "mac_address": "00:1A:2B:3C:4D:A0",
        "ip_address": None,
        "firmware_version": "1.0.0",
        "status": "active",
        "capabilities": ["adc"],
        "sensors": ["ph"]
    },
    {
        "name": "EC-Sensor-01",
        "device_type": "sensor",
        "location": "Nutrient Reservoir",
        "description": "Electrical Conductivity Sensor",
        "mac_address": "00:1A:2B:3C:4D:A1",
        "ip_address": None,
        "firmware_version": "1.0.0",
        "status": "active",
        "capabilities": ["adc"],
        "sensors": ["ec", "tds"]
    },
    
    # Pump Controllers
    {
        "name": "Pump-Controller-01",
        "device_type": "actuator",
        "location": "Nutrient System",
        "description": "Peristaltic Pump Controller for nutrients",
        "mac_address": "00:1A:2B:3C:4D:B0",
        "ip_address": None,
        "firmware_version": "1.1.0",
        "status": "active",
        "capabilities": ["pwm", "flow_control"],
        "sensors": ["flow_rate"]
    },
    {
        "name": "Misting-Pump-01",
        "device_type": "actuator",
        "location": "Fruiting Chamber",
        "description": "High-pressure misting pump",
        "mac_address": "00:1A:2B:3C:4D:B1",
        "ip_address": None,
        "firmware_version": "1.0.0",
        "status": "active",
        "capabilities": ["relay", "timer"],
        "sensors": []
    },
]

print(f"Registering {len(devices)} devices to MINDEX database...")

# Build SQL statements
sql_inserts = []
for device in devices:
    name = device["name"]
    device_type = device["device_type"]
    location = device["location"]
    description = device["description"].replace("'", "''")
    mac = device["mac_address"]
    ip = device["ip_address"] if device["ip_address"] else "NULL"
    firmware = device["firmware_version"]
    status = device["status"]
    capabilities = json.dumps(device["capabilities"]).replace("'", "''")
    sensors = json.dumps(device["sensors"]).replace("'", "''")
    
    if ip != "NULL":
        ip = f"'{ip}'"
    
    sql_inserts.append(f"""
        INSERT INTO registry.devices (name, device_type, location, description, mac_address, ip_address, firmware_version, status, capabilities, sensors)
        VALUES ('{name}', '{device_type}', '{location}', '{description}', '{mac}', {ip}, '{firmware}', '{status}', '{capabilities}'::jsonb, '{sensors}'::jsonb)
        ON CONFLICT (name) DO UPDATE SET
            device_type = EXCLUDED.device_type,
            location = EXCLUDED.location,
            description = EXCLUDED.description,
            mac_address = EXCLUDED.mac_address,
            ip_address = EXCLUDED.ip_address,
            firmware_version = EXCLUDED.firmware_version,
            status = EXCLUDED.status,
            capabilities = EXCLUDED.capabilities,
            sensors = EXCLUDED.sensors;
    """)

sql_batch = "".join(sql_inserts)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(mindex_host, username=user, password=passwd, timeout=30)
    print(f"Connected to MINDEX VM at {mindex_host}")
    
    # First ensure the devices table has all needed columns
    alter_sql = """
        ALTER TABLE registry.devices ADD COLUMN IF NOT EXISTS device_type VARCHAR(100);
        ALTER TABLE registry.devices ADD COLUMN IF NOT EXISTS location VARCHAR(255);
        ALTER TABLE registry.devices ADD COLUMN IF NOT EXISTS mac_address VARCHAR(50);
        ALTER TABLE registry.devices ADD COLUMN IF NOT EXISTS ip_address VARCHAR(50);
        ALTER TABLE registry.devices ADD COLUMN IF NOT EXISTS firmware_version VARCHAR(50);
        ALTER TABLE registry.devices ADD COLUMN IF NOT EXISTS capabilities JSONB DEFAULT '[]'::jsonb;
        ALTER TABLE registry.devices ADD COLUMN IF NOT EXISTS sensors JSONB DEFAULT '[]'::jsonb;
    """
    
    cmd = f'''docker exec -i mindex-postgres psql -U mycosoft -d mindex << 'EOSQL'
{alter_sql}
EOSQL'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"Schema updated")
    
    # Execute batch insert
    cmd = f'''docker exec -i mindex-postgres psql -U mycosoft -d mindex << 'EOSQL'
{sql_batch}
EOSQL'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if err and "ERROR" in err:
        print(f"Insert errors: {err}")
    else:
        print("Devices inserted successfully")
    
    # Get total count
    cmd = 'docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT COUNT(*) as total FROM registry.devices;"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"\nTotal devices registered:\n{out}")
    
    # Get summary by type
    cmd = 'docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT device_type, COUNT(*) FROM registry.devices GROUP BY device_type ORDER BY device_type;"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"Devices by type:\n{out}")
    
    # Show sample devices
    cmd = 'docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT name, device_type, location, status FROM registry.devices ORDER BY device_type, name LIMIT 15;"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"Sample devices:\n{out}")
    
    ssh.close()
    print("Device registration complete!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
