"""
Debug device registration - insert one device with full error output.
Created: February 5, 2026
"""
import paramiko
import os

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = os.getenv("SANDBOX_PASSWORD", "Mushroom1!Mushroom1!")

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(mindex_host, username=user, password=passwd, timeout=30)
    print(f"Connected to MINDEX VM at {mindex_host}")
    
    # Check table structure first
    cmd = '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "\\d registry.devices"'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"Table structure:\n{out}")
    
    # Try a simple insert
    insert_sql = """
        INSERT INTO registry.devices (id, name, device_type, location, description, mac_address, ip_address, firmware_version, status, capabilities, sensors)
        VALUES (gen_random_uuid(), 'Test-Device-001', 'sensor', 'Test Location', 'Test device for debugging', '00:00:00:00:00:01', '192.168.0.200', '1.0.0', 'active', '["test"]'::jsonb, '["temperature"]'::jsonb);
    """
    
    cmd = f'''docker exec -i mindex-postgres psql -U mycosoft -d mindex << 'EOSQL'
{insert_sql}
EOSQL'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    print(f"Insert output: {out}")
    print(f"Insert stderr: {err}")
    
    # Check if it was inserted
    cmd = 'docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT name, device_type FROM registry.devices LIMIT 5;"'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"Devices now:\n{out}")
    
    ssh.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
