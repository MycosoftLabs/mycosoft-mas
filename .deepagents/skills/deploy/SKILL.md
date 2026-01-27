---
name: deploy
description: Deploy code to VM environments via Docker
version: 1.0
tags: ['ops', 'docker', 'deployment']
---

## Deploy Skill

This skill handles deployment of code to VM environments.

### Steps:
1. SSH to target VM
2. Pull latest code from git
3. Rebuild Docker containers
4. Restart services
5. Verify health

### Required Tools:
- ssh_exec
- docker_exec
- health_check

