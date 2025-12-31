#!/usr/bin/env python3
"""
Script to fix disconnection issues in mycobrain_service_standalone.py
This adds connection keepalive and better error handling
"""

import re

file_path = "mycobrain_service_standalone.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Add device ID detection on connection (first occurrence only)
old_connect = """            # Test read/write - send newline to wake device
            try:
                ser.write(b'\\n')
                time.sleep(0.1)
            except:
                pass  # Continue even if write fails
            
            # Store device info with serial handle
            devices[device_id] = {
                "device_id": device_id,
                "port": port,
                "baudrate": baudrate,
                "status": "connected",
                "connected_at": datetime.now().isoformat(),
                "serial_handle": ser  # Keep handle open for commands
            }
            
            logger.info(f"Connected to device {device_id} on {port}")"""

new_connect = """            # Test read/write - send newline to wake device and try to get device ID
            actual_device_id = device_id
            try:
                ser.write(b'\\n')
                time.sleep(0.3)  # Give device time to respond
                
                # Try to read device identification
                if ser.in_waiting > 0:
                    response_bytes = ser.read(ser.in_waiting)
                    response = response_bytes.decode('utf-8', errors='replace').strip()
                    
                    # Look for device ID in response (e.g., "mycobrain-side-a-COM5")
                    device_id_match = re.search(r'mycobrain-[^\\s\\n]+', response, re.IGNORECASE)
                    if device_id_match:
                        actual_device_id = device_id_match.group(0)
                        logger.info(f"Detected device ID from board: {actual_device_id}")
            except Exception as e:
                logger.warning(f"Could not read device ID from board: {e}")
                pass  # Continue with default device_id
            
            # Store device info with serial handle
            devices[actual_device_id] = {
                "device_id": actual_device_id,
                "port": port,
                "baudrate": baudrate,
                "status": "connected",
                "connected_at": datetime.now().isoformat(),
                "serial_handle": ser,  # Keep handle open for commands
                "last_activity": datetime.now().isoformat(),  # Track last activity
            }
            
            # If device_id changed, remove old entry
            if actual_device_id != device_id and device_id in devices:
                del devices[device_id]
            
            logger.info(f"Connected to device {actual_device_id} on {port}")"""

# Replace first occurrence only
content = content.replace(old_connect, new_connect, 1)

# Fix 2: Improve command endpoint with better reconnection (first occurrence only)
old_command = """        # Get or create serial connection
        if "serial_handle" in device:
            ser = device["serial_handle"]
            # Check if still open
            if not (hasattr(ser, "is_open") and ser.is_open):
                # Reconnect
                try:
                    ser = serial.Serial(device.get("port"), device.get("baudrate", 115200), timeout=2)
                    devices[device_id]["serial_handle"] = ser
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to reconnect: {str(e)}")
        else:
            # Create new connection
            try:
                ser = serial.Serial(device.get("port"), device.get("baudrate", 115200), timeout=2)
                devices[device_id]["serial_handle"] = ser
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to connect: {str(e)}")
        
        # Clear buffers
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except:
            pass
        
        # Send command as JSON string
        cmd_str = json.dumps(request.command) + "\\n"
        ser.write(cmd_str.encode('utf-8'))
        ser.flush()
        
        # Read response
        time.sleep(0.5)  # Wait for response
        response = ""
        if ser.in_waiting > 0:
            response_bytes = ser.read(ser.in_waiting)
            response = response_bytes.decode('utf-8', errors='replace')"""

new_command = """        # Get or create serial connection with better error handling and reconnection
        ser = None
        if "serial_handle" in device:
            ser = device["serial_handle"]
            # Check if still open and valid
            try:
                if hasattr(ser, "is_open") and ser.is_open:
                    # Test connection by checking if port is still accessible
                    try:
                        _ = ser.in_waiting  # This will raise if connection is bad
                    except:
                        ser = None  # Connection is bad, need to reconnect
                        logger.warning(f"Serial connection for {device_id} is invalid, reconnecting...")
                else:
                    ser = None  # Connection is closed
            except Exception as e:
                logger.warning(f"Error checking serial connection for {device_id}: {e}")
                ser = None  # Connection is invalid
        
        # Reconnect if needed
        if not ser:
            try:
                # Close old connection if it exists
                if "serial_handle" in device:
                    try:
                        old_ser = device["serial_handle"]
                        if hasattr(old_ser, "close"):
                            old_ser.close()
                    except:
                        pass
                
                # Create new connection
                ser = serial.Serial(
                    device.get("port"), 
                    device.get("baudrate", 115200), 
                    timeout=2,
                    write_timeout=2
                )
                devices[device_id]["serial_handle"] = ser
                devices[device_id]["last_activity"] = datetime.now().isoformat()
                logger.info(f"Reconnected serial port for device {device_id}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to connect to device: {str(e)}")
        
        # Update last activity
        devices[device_id]["last_activity"] = datetime.now().isoformat()
        
        # Clear buffers
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except:
            pass
        
        # Format command based on structure
        # Support both formats: {"command": {"cmd": "led rgb 255 0 0"}} and {"cmd": "led rgb 255 0 0"}
        cmd_dict = request.command
        if isinstance(cmd_dict, dict):
            if "command" in cmd_dict and isinstance(cmd_dict["command"], dict):
                # Format: {"command": {"cmd": "led rgb 255 0 0"}}
                cmd_str = cmd_dict["command"].get("cmd", "")
            elif "cmd" in cmd_dict:
                # Format: {"cmd": "led rgb 255 0 0"}
                cmd_str = cmd_dict["cmd"]
            else:
                # Fallback: convert entire dict to string
                cmd_str = json.dumps(cmd_dict)
        else:
            cmd_str = str(cmd_dict)
        
        # Send command as string with newline
        cmd_bytes = (cmd_str + "\\n").encode('utf-8')
        ser.write(cmd_bytes)
        ser.flush()
        
        # Read response with timeout
        time.sleep(0.3)  # Wait for response
        response = ""
        max_attempts = 5
        for attempt in range(max_attempts):
            if ser.in_waiting > 0:
                response_bytes = ser.read(ser.in_waiting)
                response += response_bytes.decode('utf-8', errors='replace')
                time.sleep(0.1)  # Wait a bit more for additional data
            else:
                break"""

# Replace first occurrence only
content = content.replace(old_command, new_command, 1)

# Add import re at the top if not present
if "import re" not in content.split("\n")[:20]:
    # Find the import section and add re
    import_line = "import os"
    if import_line in content:
        content = content.replace(import_line, f"{import_line}\nimport re", 1)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed disconnection issues in mycobrain_service_standalone.py")

























