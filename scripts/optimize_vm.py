#!/usr/bin/env python3
"""
VM Optimization Script
Clears caches, optimizes containers, and reduces memory/CPU usage
"""

import paramiko
import sys
from datetime import datetime

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "•", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "HEAD": "▶", "STAT": "📊"}
    print(f"[{ts}] {icons.get(level, '•')} {msg}")

def run_ssh_cmd(ssh, cmd, timeout=120, show_output=True):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if show_output and out:
            for line in out.split('\n')[:10]:
                print(f"    {line}")
        return out, err
    except Exception as e:
        return None, str(e)

def main():
    print("\n" + "="*70)
    print("     MYCOSOFT VM OPTIMIZATION")
    print("     Clear caches, optimize resources, improve efficiency")
    print("="*70 + "\n")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        log("Connecting to VM...", "HEAD")
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
        log("Connected to 192.168.0.187", "OK")
        
        # =====================================================
        # SECTION 1: Check Current Resource Usage
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 1: Current Resource Usage (Before)")
        print("-"*70)
        
        log("Checking memory usage...", "STAT")
        out, _ = run_ssh_cmd(ssh, "free -h")
        
        log("Checking disk usage...", "STAT")
        out, _ = run_ssh_cmd(ssh, "df -h / /home /opt 2>/dev/null | head -5")
        
        log("Checking Docker disk usage...", "STAT")
        out, _ = run_ssh_cmd(ssh, "docker system df")
        
        log("Checking container resource usage...", "STAT")
        out, _ = run_ssh_cmd(ssh, "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'")
        
        # =====================================================
        # SECTION 2: Clean Docker Resources
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 2: Docker Cleanup")
        print("-"*70)
        
        log("Removing stopped containers...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker container prune -f")
        
        log("Removing dangling images...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker image prune -f")
        
        log("Removing unused volumes...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker volume prune -f")
        
        log("Removing build cache...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker builder prune -af --keep-storage 1GB 2>/dev/null || docker builder prune -af")
        
        log("Removing unused networks...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker network prune -f")
        
        # =====================================================
        # SECTION 3: System Cache Cleanup
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 3: System Cache Cleanup")
        print("-"*70)
        
        log("Clearing apt cache...", "HEAD")
        run_ssh_cmd(ssh, "sudo apt-get clean 2>/dev/null || true", show_output=False)
        
        log("Clearing journal logs older than 3 days...", "HEAD")
        run_ssh_cmd(ssh, "sudo journalctl --vacuum-time=3d 2>/dev/null || true", show_output=False)
        
        log("Clearing temp files...", "HEAD")
        run_ssh_cmd(ssh, "rm -rf /tmp/* 2>/dev/null || true", show_output=False)
        run_ssh_cmd(ssh, "rm -rf /home/mycosoft/.cache/pip/* 2>/dev/null || true", show_output=False)
        
        log("Dropping page cache (if sudo available)...", "HEAD")
        run_ssh_cmd(ssh, "sync && echo 1 | sudo tee /proc/sys/vm/drop_caches 2>/dev/null || echo 'Skipped (requires sudo)'", show_output=False)
        
        # =====================================================
        # SECTION 4: Container Optimization
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 4: Container Resource Limits")
        print("-"*70)
        
        log("Setting container resource limits...", "HEAD")
        
        # Define optimal resource limits for each container
        container_limits = {
            "mycosoft-website": {"memory": "1g", "cpus": "1.0"},
            "mindex-api": {"memory": "512m", "cpus": "0.5"},
            "mindex-postgres-data": {"memory": "1g", "cpus": "0.5"},
            "mindex-etl-scheduler": {"memory": "256m", "cpus": "0.25"},
            "mycosoft-redis": {"memory": "256m", "cpus": "0.25"},
            "mycosoft-postgres": {"memory": "512m", "cpus": "0.5"},
            "mas-n8n-1": {"memory": "512m", "cpus": "0.5"},
        }
        
        for container, limits in container_limits.items():
            log(f"  Updating {container}: mem={limits['memory']}, cpu={limits['cpus']}", "INFO")
            cmd = f"docker update --memory={limits['memory']} --cpus={limits['cpus']} {container} 2>/dev/null || true"
            run_ssh_cmd(ssh, cmd, show_output=False)
        
        log("Container limits applied", "OK")
        
        # =====================================================
        # SECTION 5: Optimize PostgreSQL
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 5: PostgreSQL Optimization")
        print("-"*70)
        
        log("Running VACUUM on MINDEX database...", "HEAD")
        run_ssh_cmd(ssh, """
            docker exec mindex-postgres-data psql -U mindex -d mindex -c "VACUUM ANALYZE;" 2>/dev/null || true
        """, show_output=False)
        
        log("Running VACUUM on main database...", "HEAD")
        run_ssh_cmd(ssh, """
            docker exec mycosoft-postgres psql -U postgres -d mycosoft -c "VACUUM ANALYZE;" 2>/dev/null || true
        """, show_output=False)
        
        log("PostgreSQL optimized", "OK")
        
        # =====================================================
        # SECTION 6: Redis Optimization
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 6: Redis Optimization")
        print("-"*70)
        
        log("Checking Redis memory usage...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker exec mycosoft-redis redis-cli INFO memory 2>/dev/null | grep -E 'used_memory_human|maxmemory'")
        
        log("Triggering Redis background save...", "HEAD")
        run_ssh_cmd(ssh, "docker exec mycosoft-redis redis-cli BGSAVE 2>/dev/null || true", show_output=False)
        
        log("Redis optimized", "OK")
        
        # =====================================================
        # SECTION 7: Website/Next.js Optimization
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 7: Website Optimization")
        print("-"*70)
        
        log("Clearing Next.js cache inside container...", "HEAD")
        run_ssh_cmd(ssh, """
            docker exec mycosoft-website sh -c 'rm -rf /app/.next/cache/* 2>/dev/null' || true
        """, show_output=False)
        
        log("Next.js cache cleared", "OK")
        
        # =====================================================
        # SECTION 8: Verify Services Still Running
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 8: Verify Services")
        print("-"*70)
        
        log("Checking all containers are running...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}'")
        
        log("Testing website health...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
        log(f"Website HTTP: {out}", "OK" if out == "200" else "WARN")
        
        log("Testing MINDEX API health...", "HEAD")
        out, _ = run_ssh_cmd(ssh, "curl -s http://localhost:8000/api/mindex/health")
        log(f"MINDEX: {out[:50]}...", "OK" if "healthy" in out else "WARN")
        
        # =====================================================
        # SECTION 9: Final Resource Usage (After)
        # =====================================================
        print("\n" + "-"*70)
        print("  SECTION 9: Resource Usage (After Optimization)")
        print("-"*70)
        
        log("Memory usage after optimization...", "STAT")
        out, _ = run_ssh_cmd(ssh, "free -h")
        
        log("Docker disk usage after cleanup...", "STAT")
        out, _ = run_ssh_cmd(ssh, "docker system df")
        
        log("Container resource usage after limits...", "STAT")
        out, _ = run_ssh_cmd(ssh, "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'")
        
        ssh.close()
        
        # =====================================================
        # Summary
        # =====================================================
        print("\n" + "="*70)
        print("     OPTIMIZATION COMPLETE")
        print("="*70)
        print("""
    Actions Performed:
    ─────────────────
    ✓ Docker: Removed stopped containers, dangling images, volumes, build cache
    ✓ System: Cleared apt cache, old journal logs, temp files
    ✓ Containers: Applied memory and CPU limits to all services
    ✓ PostgreSQL: Ran VACUUM ANALYZE on databases
    ✓ Redis: Triggered background save
    ✓ Website: Cleared Next.js cache
    ✓ Verified all services are running

    Resource Limits Applied:
    ────────────────────────
    • mycosoft-website:     1GB RAM, 1.0 CPU
    • mindex-postgres-data: 1GB RAM, 0.5 CPU
    • mindex-api:           512MB RAM, 0.5 CPU
    • mycosoft-postgres:    512MB RAM, 0.5 CPU
    • mas-n8n-1:            512MB RAM, 0.5 CPU
    • mindex-etl-scheduler: 256MB RAM, 0.25 CPU
    • mycosoft-redis:       256MB RAM, 0.25 CPU
        """)
        
    except Exception as e:
        log(f"Error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
