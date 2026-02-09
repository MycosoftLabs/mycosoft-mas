"""
Nuclear MCP fix - clear ALL MCP state, browser partitions, and caches.
Forces completely fresh OAuth flow on next Cursor startup.
"""
import sqlite3
import json
import shutil
import os
from datetime import datetime

print("=" * 60)
print("NUCLEAR MCP FIX - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 60)

APPDATA = os.path.join(os.environ["APPDATA"], "Cursor")
HOME = os.environ["USERPROFILE"]
DB_PATH = os.path.join(APPDATA, "User", "globalStorage", "state.vscdb")
MCP_JSON = os.path.join(HOME, ".cursor", "mcp.json")

# Step 1: Backup state DB
backup = DB_PATH + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy2(DB_PATH, backup)
print(f"\n[1] Backed up state DB")

# Step 2: Nuke ALL MCP entries from state DB
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Find and delete everything MCP related
c.execute("SELECT key FROM ItemTable WHERE key LIKE '%mcp%' OR key LIKE '%Notion%' OR key LIKE '%supabase%' OR key LIKE '%notion%'")
mcp_keys = [r[0] for r in c.fetchall()]
print(f"\n[2] Removing {len(mcp_keys)} MCP entries from state DB:")
for key in mcp_keys:
    c.execute("DELETE FROM ItemTable WHERE key = ?", (key,))
    print(f"    Deleted: {key[:80]}")

conn.commit()
conn.close()
print("    State DB cleaned.")

# Step 3: Clear npx cache
npx_cache = os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm-cache", "_npx")
if os.path.exists(npx_cache):
    shutil.rmtree(npx_cache, ignore_errors=True)
    print(f"\n[3] Cleared npx cache")
else:
    print(f"\n[3] npx cache already clean")

# Step 4: Clear Cursor's internal browser partitions (where OAuth cookies live)
partitions_dir = os.path.join(APPDATA, "Partitions")
cleared_partitions = 0
if os.path.exists(partitions_dir):
    for partition in os.listdir(partitions_dir):
        partition_path = os.path.join(partitions_dir, partition)
        if os.path.isdir(partition_path):
            # Clear cookies, local storage, session storage in each partition
            for subdir in ["Cookies", "Local Storage", "Session Storage", "Cache", "Code Cache"]:
                target = os.path.join(partition_path, subdir)
                if os.path.exists(target):
                    try:
                        shutil.rmtree(target, ignore_errors=True)
                        cleared_partitions += 1
                    except:
                        pass
            # Also clear cookie files directly
            for fname in os.listdir(partition_path):
                if "cookie" in fname.lower() or "session" in fname.lower():
                    try:
                        fpath = os.path.join(partition_path, fname)
                        if os.path.isfile(fpath):
                            os.remove(fpath)
                            cleared_partitions += 1
                    except:
                        pass
print(f"\n[4] Cleared {cleared_partitions} browser partition caches")

# Step 5: Clear main Cursor session/cache
for subdir in ["Session Storage", "Local Storage", "Cache", "Code Cache"]:
    target = os.path.join(APPDATA, subdir)
    if os.path.exists(target):
        try:
            shutil.rmtree(target, ignore_errors=True)
            print(f"    Cleared {subdir}")
        except:
            print(f"    Could not clear {subdir} (may be locked)")

# Step 6: Write clean mcp.json
mcp_config = {
    "mcpServers": {
        "Notion": {
            "url": "https://mcp.notion.com/mcp"
        },
        "supabase": {
            "url": "https://mcp.supabase.com/mcp?project_ref=hnevnsxnhfibhbsipqvz"
        }
    }
}
with open(MCP_JSON, 'w') as f:
    json.dump(mcp_config, f, indent=2)
print(f"\n[5] Wrote clean mcp.json")

# Step 7: Check Cursor version
settings_path = os.path.join(APPDATA, "User", "settings.json")
if os.path.exists(settings_path):
    print(f"\n[6] Cursor settings exist at {settings_path}")

# Also add MCP timeout settings to Cursor settings
try:
    with open(settings_path, 'r') as f:
        settings = json.load(f)
    
    # Add MCP-friendly settings
    settings["remote.MCP.connectionTimeout"] = 30000
    settings["remote.MCP.keepAliveInterval"] = 15000
    
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
    print("    Added MCP timeout settings")
except Exception as e:
    print(f"    Could not update settings: {e}")

print("\n" + "=" * 60)
print("ALL DONE. INSTRUCTIONS:")
print("=" * 60)
print("""
1. CLOSE Cursor completely (File > Exit)
2. Open PowerShell (Win+R > powershell) and run:
   
   taskkill /F /IM Cursor.exe
   
3. Wait 5 seconds, then reopen Cursor
4. Open this workspace (mycosoft-mas)
5. Go to Cursor Settings (gear icon) > MCP
6. You should see Notion and Supabase listed
7. Click Connect on each one
8. An OAuth popup SHOULD open in your browser now
   (all stale state has been wiped)
""")
