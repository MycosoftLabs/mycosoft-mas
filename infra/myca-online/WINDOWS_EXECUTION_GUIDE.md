# Windows Execution Guide for MYCA Bootstrap

## Important: Running on Windows

You are currently on Windows. The bootstrap script (`bootstrap_myca.sh`) is a **bash script** that needs to run on **Linux/Ubuntu**.

Based on your infrastructure notes, you have an **Ubuntu control node** where this should be executed.

## Execution Options

### Option 1: Transfer to Ubuntu Control Node (RECOMMENDED)

1. **Copy the repository to your Ubuntu machine**:
   ```powershell
   # From Windows PowerShell
   scp -r "C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas" user@ubuntu-control-node:/home/user/
   ```

2. **SSH to Ubuntu control node**:
   ```powershell
   ssh user@ubuntu-control-node
   ```

3. **Navigate to repo and run bootstrap**:
   ```bash
   cd ~/mycosoft-mas
   bash infra/myca-online/bootstrap_myca.sh dry-run
   bash infra/myca-online/bootstrap_myca.sh apply
   bash infra/myca-online/bootstrap_myca.sh verify
   ```

### Option 2: Use WSL (Windows Subsystem for Linux)

If you have WSL installed:

1. **Open WSL terminal** (Ubuntu on Windows)

2. **Navigate to the repo** (Windows drives are mounted at /mnt/):
   ```bash
   cd /mnt/c/Users/admin2/Desktop/MYCOSOFT/CODE/MAS/mycosoft-mas
   ```

3. **Install required packages** (if not already installed):
   ```bash
   sudo apt update
   sudo apt install -y curl jq vault docker.io
   ```

4. **Run bootstrap**:
   ```bash
   bash infra/myca-online/bootstrap_myca.sh dry-run
   bash infra/myca-online/bootstrap_myca.sh apply
   bash infra/myca-online/bootstrap_myca.sh verify
   ```

### Option 3: Git Bash (Limited Support)

Git Bash on Windows has limited Linux command support. Some commands may fail.

**Not recommended for production deployment.**

## Prerequisites for Ubuntu Control Node

Ensure your Ubuntu control node has:

1. **Docker** with nvidia-docker (for GPU):
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **NVIDIA drivers** (for GPU):
   ```bash
   # Check GPU
   nvidia-smi
   
   # Install nvidia-docker if needed
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

3. **Common tools**:
   ```bash
   sudo apt install -y curl jq git nfs-common cifs-utils
   ```

4. **Network access to**:
   - Proxmox nodes (192.168.0.202, 192.168.0.2, 192.168.0.131)
   - UniFi UDM (192.168.0.1)
   - NAS (your IP)

5. **Vault** (will be installed by bootstrap if missing):
   ```bash
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt update && sudo apt install vault
   ```

## Recommended: Run from Ubuntu Control Node

Given the hardware requirements (GPU, UART, NAS mounting), this bootstrap is designed to run on the **Ubuntu control node** mentioned in your setup.

### Transfer Steps

1. **From Windows PowerShell**:
   ```powershell
   # Ensure you're in the repo directory
   cd C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas
   
   # Create tarball
   tar -czf mycosoft-mas.tar.gz .
   
   # Copy to Ubuntu control node
   scp mycosoft-mas.tar.gz user@ubuntu-ip:~
   ```

2. **On Ubuntu control node**:
   ```bash
   # Extract
   cd ~
   tar -xzf mycosoft-mas.tar.gz -C mycosoft-mas
   cd mycosoft-mas
   
   # Make bootstrap executable
   chmod +x infra/myca-online/bootstrap_myca.sh
   
   # Run dry-run
   bash infra/myca-online/bootstrap_myca.sh dry-run
   
   # If all checks pass, run apply
   bash infra/myca-online/bootstrap_myca.sh apply
   ```

## Expected Ubuntu Control Node Setup

Based on your prompt:

- **Location**: Local Ubuntu machine
- **GPU**: RTX 5090 (connected to this machine)
- **UART**: MycoBrain USB UART (ttyUSB* or ttyACM*)
- **Network**: Access to Proxmox, UniFi, NAS
- **Docker**: Installed with GPU support
- **Purpose**: Control node for MYCA MAS infrastructure

## What Happens During Bootstrap

### 1. Dry Run (`bash infra/myca-online/bootstrap_myca.sh dry-run`)

Checks:
- ✓ curl, docker, jq installed
- ✓ Vault status
- ✓ Proxmox connectivity (3 nodes)
- ✓ UniFi connectivity
- ✓ NAS mount status
- ✓ GPU availability (nvidia-smi)
- ✓ UART devices

**Takes**: ~30 seconds  
**Changes**: None (read-only checks)

### 2. Apply (`bash infra/myca-online/bootstrap_myca.sh apply`)

Interactive setup:
1. Install Vault (prompts for confirmation)
2. Initialize Vault (generates unseal keys)
3. Configure KV v2 and AppRole
4. **YOU PROVIDE**: Proxmox API token or SSH to create
5. Validate token across all Proxmox nodes
6. **YOU PROVIDE**: UniFi API key
7. Validate UniFi key
8. **YOU PROVIDE**: NAS configuration (IP, protocol, credentials)
9. Mount NAS to /mnt/mycosoft-nas
10. Create logs directory on NAS
11. Test GPU (if available)
12. Detect UART devices
13. Generate docker-compose.myca.yml
14. Deploy MYCA containers
15. Wait for health checks
16. Generate output files

**Takes**: 5-15 minutes (depends on prompts)  
**Changes**: Installs Vault, mounts NAS, deploys containers

### 3. Verify (`bash infra/myca-online/bootstrap_myca.sh verify`)

Verifies:
- ✓ Vault running and unsealed
- ✓ Proxmox token valid
- ✓ UniFi key valid
- ✓ NAS mounted
- ✓ GPU available
- ✓ MYCA health endpoint OK
- ✓ MYCA UI endpoint OK

**Takes**: ~10 seconds  
**Changes**: None (read-only checks)

## After Successful Bootstrap

You'll have:

1. **MYCA API**: http://localhost:8001
2. **MYCA UI**: http://localhost:3001
3. **Vault**: http://127.0.0.1:8200
4. **NAS mounted**: /mnt/mycosoft-nas
5. **Audit logs**: /mnt/mycosoft-nas/logs/audit.jsonl
6. **UART logs**: /mnt/mycosoft-nas/logs/uart_ingest.jsonl
7. **GPU logs**: /mnt/mycosoft-nas/logs/gpu_runner.jsonl

## Testing After Bootstrap

```bash
# Health check
curl http://localhost:8001/health

# Status
curl http://localhost:8001/api/status

# Proxmox inventory
curl -X POST http://localhost:8001/api/proxmox/inventory

# UniFi topology
curl -X POST http://localhost:8001/api/unifi/topology

# GPU test
curl -X POST http://localhost:8001/api/gpu/run_test

# UART logs
curl http://localhost:8001/api/uart/tail?lines=100

# NAS status
curl http://localhost:8001/api/nas/status
```

## Stopping/Restarting

```bash
# Stop
docker-compose -f docker-compose.yml -f docker-compose.myca.yml down

# Start (basic)
docker-compose -f docker-compose.yml up -d

# Start (with infrastructure)
docker-compose -f docker-compose.yml -f docker-compose.myca.yml \
  --profile hardware --profile gpu up -d
```

## Troubleshooting

### "Command not found: bash"

You're in PowerShell. You need to run this on Linux (Ubuntu control node or WSL).

### "Permission denied"

Make script executable:
```bash
chmod +x infra/myca-online/bootstrap_myca.sh
```

### "Cannot connect to Proxmox"

Check network connectivity:
```bash
ping 192.168.0.202
curl -k https://192.168.0.202:8006/api2/json/version
```

### "GPU not detected"

Install NVIDIA drivers:
```bash
nvidia-smi
# If fails, install drivers and nvidia-docker
```

### "UART devices not found"

Check USB connections:
```bash
ls -l /dev/ttyUSB* /dev/ttyACM*
# Add user to dialout group
sudo usermod -a -G dialout $USER
```

## Security Notes

- **No passwords stored in files** - all entered interactively
- **Secrets in Vault only** - encrypted at rest
- **Confirmation gates** - write operations require confirm=true
- **Audit trail** - all actions logged to NAS
- **AppRole auth** - containers use AppRole, not root token

## Support

See `infra/myca-online/README.md` for comprehensive documentation.

See `infra/myca-online/IMPLEMENTATION_SUMMARY.md` for architecture details.

---

**Next Step**: Transfer this repo to your Ubuntu control node and run the bootstrap there.
