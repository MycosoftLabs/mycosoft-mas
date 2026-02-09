"""Restore corrupted files from git history."""
import subprocess
import os

corrupted_files = [
    "mycosoft_mas/agents/drone_agent.py",
    "mycosoft_mas/agents/enums.py",
    "mycosoft_mas/agents/experiment_agent.py",
    "mycosoft_mas/agents/finance_admin_agent.py",
    "mycosoft_mas/agents/interfaces.py",
    "mycosoft_mas/agents/ip_tokenization_agent.py",
    "mycosoft_mas/agents/mycology_knowledge_agent.py",
    "mycosoft_mas/agents/opportunity_scout.py",
    "mycosoft_mas/agents/orchestrator.py",
    "mycosoft_mas/agents/project_management_agent.py",
    "mycosoft_mas/agents/project_manager_agent.py",
    "mycosoft_mas/agents/sales_agent.py",
    "mycosoft_mas/agents/wifisense_agent.py",
    "mycosoft_mas/integrations/azure_client.py",
    "mycosoft_mas/integrations/defense_client.py",
    "mycosoft_mas/integrations/mindex_client.py",
    "mycosoft_mas/integrations/proxmox_integration.py",
    "mycosoft_mas/integrations/twilio_integration.py",
    "mycosoft_mas/integrations/unifi_integration.py",
    "mycosoft_mas/integrations/unified_integration_manager.py",
    "mycosoft_mas/integrations/website_client.py",
    "mycosoft_mas/security/integrity_service.py",
    "mycosoft_mas/security/rbac.py",
    "mycosoft_mas/voice/personaplex_bridge.py",
]

restored = 0
failed = []

for filepath in corrupted_files:
    # Find the last commit that modified this file
    result = subprocess.run(
        ['git', 'log', '--oneline', '-1', '--', filepath],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0 or not result.stdout.strip():
        print(f"No git history for {filepath}")
        failed.append(filepath)
        continue
    
    commit_hash = result.stdout.strip().split()[0]
    
    # Get the file content from that commit
    result = subprocess.run(
        ['git', 'show', f'{commit_hash}:{filepath}'],
        capture_output=True
    )
    
    if result.returncode != 0:
        print(f"Could not retrieve {filepath} from {commit_hash}")
        failed.append(filepath)
        continue
    
    # Decode and write
    try:
        content = result.stdout.decode('utf-8')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write the file with proper UTF-8 encoding
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        
        print(f"Restored: {filepath}")
        restored += 1
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        failed.append(filepath)

print(f"\nRestored {restored} files")
if failed:
    print(f"Failed to restore {len(failed)} files:")
    for f in failed:
        print(f"  - {f}")
