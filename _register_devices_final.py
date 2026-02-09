"""
Register all MycoBrain devices in the MINDEX PostgreSQL database.
Created: February 5, 2026 - Final version with proper schema
"""
import paramiko
import os
import json

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = os.getenv("SANDBOX_PASSWORD", "Mushroom1!Mushroom1!")

# Device definitions with comprehensive metadata
devices = [
    # Core Devices
    {"device_id": "SPOREBASE-001", "name": "SporeBase-001", "type": "mycobrain", "device_type": "controller", 
     "location": "Lab Rack 1", "description": "SporeBase Primary Controller - ESP32-S3 with touchscreen",
     "mac_address": "00:1A:2B:3C:4D:01", "ip_address": "192.168.0.150", "firmware_version": "2.1.0", "status": "active",
     "capabilities": ["touchscreen", "wifi", "bluetooth", "mqtt", "nfc"], "sensors": ["temperature", "humidity", "co2", "light"]},
    {"device_id": "MUSHROOM1-MAIN", "name": "Mushroom1-Main", "type": "mycobrain", "device_type": "controller",
     "location": "Grow Chamber 1", "description": "Mushroom1 Main Control Unit - Full environmental control",
     "mac_address": "00:1A:2B:3C:4D:02", "ip_address": "192.168.0.151", "firmware_version": "2.0.5", "status": "active",
     "capabilities": ["wifi", "mqtt", "modbus", "relay_control"], "sensors": ["temperature", "humidity", "co2", "weight"]},
    # Environmental Sensors
    {"device_id": "TH-SENSOR-01", "name": "TempHumid-Sensor-01", "type": "sensor", "device_type": "sensor",
     "location": "Grow Chamber 1 - Top", "description": "SHT40 Temperature and Humidity Sensor",
     "mac_address": "00:1A:2B:3C:4D:10", "ip_address": None, "firmware_version": "1.2.0", "status": "active",
     "capabilities": ["i2c"], "sensors": ["temperature", "humidity"]},
    {"device_id": "TH-SENSOR-02", "name": "TempHumid-Sensor-02", "type": "sensor", "device_type": "sensor",
     "location": "Grow Chamber 1 - Bottom", "description": "SHT40 Temperature and Humidity Sensor",
     "mac_address": "00:1A:2B:3C:4D:11", "ip_address": None, "firmware_version": "1.2.0", "status": "active",
     "capabilities": ["i2c"], "sensors": ["temperature", "humidity"]},
    {"device_id": "CO2-SENSOR-01", "name": "CO2-Sensor-01", "type": "sensor", "device_type": "sensor",
     "location": "Grow Chamber 1", "description": "SCD41 CO2 Sensor with Temperature and Humidity",
     "mac_address": "00:1A:2B:3C:4D:20", "ip_address": None, "firmware_version": "1.3.1", "status": "active",
     "capabilities": ["i2c"], "sensors": ["co2", "temperature", "humidity"]},
    {"device_id": "CO2-SENSOR-02", "name": "CO2-Sensor-02", "type": "sensor", "device_type": "sensor",
     "location": "Fruiting Chamber", "description": "SCD41 CO2 Sensor",
     "mac_address": "00:1A:2B:3C:4D:21", "ip_address": None, "firmware_version": "1.3.1", "status": "active",
     "capabilities": ["i2c"], "sensors": ["co2", "temperature", "humidity"]},
    {"device_id": "LIGHT-SENSOR-01", "name": "Light-Sensor-01", "type": "sensor", "device_type": "sensor",
     "location": "Grow Chamber 1 - Canopy", "description": "TSL2591 High Dynamic Range Light Sensor",
     "mac_address": "00:1A:2B:3C:4D:30", "ip_address": None, "firmware_version": "1.0.2", "status": "active",
     "capabilities": ["i2c"], "sensors": ["lux", "full_spectrum", "infrared"]},
    {"device_id": "LIGHT-SENSOR-02", "name": "Light-Sensor-02", "type": "sensor", "device_type": "sensor",
     "location": "Fruiting Chamber", "description": "TSL2591 Light Sensor",
     "mac_address": "00:1A:2B:3C:4D:31", "ip_address": None, "firmware_version": "1.0.2", "status": "active",
     "capabilities": ["i2c"], "sensors": ["lux", "full_spectrum", "infrared"]},
    {"device_id": "SCALE-SENSOR-01", "name": "Scale-Sensor-01", "type": "sensor", "device_type": "sensor",
     "location": "Grow Chamber 1 - Tray 1", "description": "HX711 Load Cell - 5kg capacity",
     "mac_address": "00:1A:2B:3C:4D:40", "ip_address": None, "firmware_version": "1.1.0", "status": "active",
     "capabilities": ["gpio"], "sensors": ["weight"]},
    {"device_id": "SCALE-SENSOR-02", "name": "Scale-Sensor-02", "type": "sensor", "device_type": "sensor",
     "location": "Grow Chamber 1 - Tray 2", "description": "HX711 Load Cell - 5kg capacity",
     "mac_address": "00:1A:2B:3C:4D:41", "ip_address": None, "firmware_version": "1.1.0", "status": "active",
     "capabilities": ["gpio"], "sensors": ["weight"]},
    # Cameras
    {"device_id": "CAM-ESP32-01", "name": "Camera-ESP32-01", "type": "camera", "device_type": "camera",
     "location": "Grow Chamber 1 - Overview", "description": "ESP32-CAM OV2640 with IR capability",
     "mac_address": "00:1A:2B:3C:4D:50", "ip_address": "192.168.0.160", "firmware_version": "1.5.0", "status": "active",
     "capabilities": ["wifi", "http_stream", "motion_detect", "ir"], "sensors": ["image", "motion"]},
    {"device_id": "CAM-ESP32-02", "name": "Camera-ESP32-02", "type": "camera", "device_type": "camera",
     "location": "Fruiting Chamber", "description": "ESP32-CAM OV2640 with Macro Lens",
     "mac_address": "00:1A:2B:3C:4D:51", "ip_address": "192.168.0.161", "firmware_version": "1.5.0", "status": "active",
     "capabilities": ["wifi", "http_stream", "timelapse"], "sensors": ["image"]},
    # Actuators
    {"device_id": "RELAY-MOD-01", "name": "Relay-Module-01", "type": "actuator", "device_type": "actuator",
     "location": "Grow Chamber 1 - Panel", "description": "8-Channel Relay Module for environmental control",
     "mac_address": "00:1A:2B:3C:4D:60", "ip_address": None, "firmware_version": "1.0.0", "status": "active",
     "capabilities": ["gpio", "8_channel"], "sensors": []},
    {"device_id": "HUMID-CTRL-01", "name": "Humidifier-Controller-01", "type": "actuator", "device_type": "actuator",
     "location": "Grow Chamber 1", "description": "Ultrasonic Humidifier with PWM control",
     "mac_address": "00:1A:2B:3C:4D:70", "ip_address": None, "firmware_version": "1.2.0", "status": "active",
     "capabilities": ["pwm", "relay"], "sensors": []},
    {"device_id": "FAN-CTRL-01", "name": "Fan-Controller-01", "type": "actuator", "device_type": "actuator",
     "location": "Grow Chamber 1 - Intake", "description": "PWM Fan Controller for ventilation",
     "mac_address": "00:1A:2B:3C:4D:71", "ip_address": None, "firmware_version": "1.1.0", "status": "active",
     "capabilities": ["pwm"], "sensors": ["rpm"]},
    {"device_id": "FAN-CTRL-02", "name": "Fan-Controller-02", "type": "actuator", "device_type": "actuator",
     "location": "Grow Chamber 1 - Exhaust", "description": "PWM Fan Controller for ventilation",
     "mac_address": "00:1A:2B:3C:4D:72", "ip_address": None, "firmware_version": "1.1.0", "status": "active",
     "capabilities": ["pwm"], "sensors": ["rpm"]},
    {"device_id": "LED-CTRL-01", "name": "LED-Controller-01", "type": "actuator", "device_type": "actuator",
     "location": "Grow Chamber 1 - Canopy", "description": "RGB+W LED Controller with spectrum control",
     "mac_address": "00:1A:2B:3C:4D:80", "ip_address": "192.168.0.170", "firmware_version": "2.0.0", "status": "active",
     "capabilities": ["wifi", "dmx", "spectrum_control"], "sensors": []},
    {"device_id": "NFC-READER-01", "name": "NFC-Reader-01", "type": "interface", "device_type": "interface",
     "location": "SporeBase-001", "description": "PN532 NFC Reader for substrate tagging",
     "mac_address": "00:1A:2B:3C:4D:90", "ip_address": None, "firmware_version": "1.0.5", "status": "active",
     "capabilities": ["spi", "nfc_read", "nfc_write"], "sensors": []},
    {"device_id": "PH-SENSOR-01", "name": "pH-Sensor-01", "type": "sensor", "device_type": "sensor",
     "location": "Nutrient Reservoir", "description": "Analog pH Sensor with calibration",
     "mac_address": "00:1A:2B:3C:4D:A0", "ip_address": None, "firmware_version": "1.0.0", "status": "active",
     "capabilities": ["adc"], "sensors": ["ph"]},
    {"device_id": "EC-SENSOR-01", "name": "EC-Sensor-01", "type": "sensor", "device_type": "sensor",
     "location": "Nutrient Reservoir", "description": "Electrical Conductivity Sensor",
     "mac_address": "00:1A:2B:3C:4D:A1", "ip_address": None, "firmware_version": "1.0.0", "status": "active",
     "capabilities": ["adc"], "sensors": ["ec", "tds"]},
    {"device_id": "PUMP-CTRL-01", "name": "Pump-Controller-01", "type": "actuator", "device_type": "actuator",
     "location": "Nutrient System", "description": "Peristaltic Pump Controller for nutrients",
     "mac_address": "00:1A:2B:3C:4D:B0", "ip_address": None, "firmware_version": "1.1.0", "status": "active",
     "capabilities": ["pwm", "flow_control"], "sensors": ["flow_rate"]},
    {"device_id": "MIST-PUMP-01", "name": "Misting-Pump-01", "type": "actuator", "device_type": "actuator",
     "location": "Fruiting Chamber", "description": "High-pressure misting pump",
     "mac_address": "00:1A:2B:3C:4D:B1", "ip_address": None, "firmware_version": "1.0.0", "status": "active",
     "capabilities": ["relay", "timer"], "sensors": []},
]

print(f"Registering {len(devices)} devices to MINDEX database...")

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(mindex_host, username=user, password=passwd, timeout=30)
    print(f"Connected to MINDEX VM at {mindex_host}")
    
    # Clear existing devices first
    clear_sql = """DELETE FROM registry.devices WHERE device_id LIKE 'SPOREBASE%' OR device_id LIKE 'MUSHROOM%' 
        OR device_id LIKE 'TH-%' OR device_id LIKE 'CO2-%' OR device_id LIKE 'LIGHT-%'
        OR device_id LIKE 'SCALE-%' OR device_id LIKE 'CAM-%' OR device_id LIKE 'RELAY-%'
        OR device_id LIKE 'HUMID-%' OR device_id LIKE 'FAN-%' OR device_id LIKE 'LED-%'
        OR device_id LIKE 'NFC-%' OR device_id LIKE 'PH-%' OR device_id LIKE 'EC-%'
        OR device_id LIKE 'PUMP-%' OR device_id LIKE 'MIST-%';"""
    
    cmd = f'''docker exec -i mindex-postgres psql -U mycosoft -d mindex << 'EOSQL'
{clear_sql}
EOSQL'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"Cleared existing devices")
    
    # Insert each device
    success_count = 0
    for device in devices:
        device_id = device["device_id"]
        name = device["name"]
        dtype = device["type"]
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
        
        insert_sql = f"""
            INSERT INTO registry.devices (device_id, name, type, device_type, location, description, mac_address, ip_address, firmware_version, status, capabilities, sensors)
            VALUES ('{device_id}', '{name}', '{dtype}', '{device_type}', '{location}', '{description}', '{mac}', {ip}, '{firmware}', '{status}', '{capabilities}'::jsonb, '{sensors}'::jsonb);
        """
        
        cmd = f'''docker exec -i mindex-postgres psql -U mycosoft -d mindex << 'EOSQL'
{insert_sql}
EOSQL'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        err = stderr.read().decode()
        if "ERROR" not in err:
            success_count += 1
        else:
            print(f"Error inserting {name}: {err.strip()}")
    
    print(f"\nInserted {success_count}/{len(devices)} devices")
    
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
    
    # Show all devices
    cmd = 'docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT name, device_type, location, status FROM registry.devices ORDER BY device_type, name;"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"All devices:\n{out}")
    
    ssh.close()
    print("Device registration complete!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
