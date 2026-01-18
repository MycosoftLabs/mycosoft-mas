#!/usr/bin/env python3
"""Create bridge service to forward MycoBrain requests from sandbox to local machine"""

# This script will create a reverse proxy/bridge that:
# 1. Runs on the local Windows machine
# 2. Listens for requests from the sandbox website
# 3. Forwards them to the local MycoBrain service (localhost:8003)
# 4. Returns responses back to the sandbox

# Since the sandbox website needs to access the local service, we need to:
# - Either expose the local service via Cloudflare tunnel
# - Or create a WebSocket bridge
# - Or update the website to use a different endpoint when accessing from sandbox

print("=" * 80)
print("MYCOBRAIN BRIDGE SETUP")
print("=" * 80)
print("\nThe MycoBrain device is on COM7 (local Windows machine)")
print("The service is running on localhost:8003 (local machine)")
print("The sandbox website needs to access this service\n")

print("SOLUTION: Update website environment variable to point to local service")
print("when accessed from development machine, or create Cloudflare tunnel")
print("to expose localhost:8003 via sandbox.mycosoft.com")

print("\nAlternatively, configure the website to use different service URL")
print("based on whether it's running locally or on sandbox.")
