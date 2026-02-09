"""Check Cursor's internal state DB for MCP auth tokens - detailed."""
import sqlite3
import json

DB_PATH = r"C:\Users\admin2\AppData\Roaming\Cursor\User\globalStorage\state.vscdb"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get ALL MCP-related keys and their full values
c.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%mcp%' OR key LIKE '%notion%' OR key LIKE '%supabase%' OR key LIKE '%Notion%'")
rows = c.fetchall()

print("=" * 80)
print("ALL MCP-RELATED ENTRIES IN CURSOR STATE DB")
print("=" * 80)

for key, value in rows:
    print(f"\nKEY: {key}")
    print(f"VALUE ({len(str(value))} chars):")
    try:
        parsed = json.loads(value)
        print(json.dumps(parsed, indent=2)[:2000])
    except:
        print(str(value)[:2000])

# Also check workspace-level state
WS_DB = r"C:\Users\admin2\AppData\Roaming\Cursor\User\workspaceStorage\0811de68144add10e59bd9b0081e0e8a\state.vscdb"
try:
    conn2 = sqlite3.connect(WS_DB)
    c2 = conn2.cursor()
    c2.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%mcp%' OR key LIKE '%notion%' OR key LIKE '%supabase%' OR key LIKE '%Notion%'")
    ws_rows = c2.fetchall()
    if ws_rows:
        print("\n" + "=" * 80)
        print("WORKSPACE-LEVEL MCP ENTRIES")
        print("=" * 80)
        for key, value in ws_rows:
            print(f"\nKEY: {key}")
            print(f"VALUE: {str(value)[:2000]}")
    conn2.close()
except Exception as e:
    print(f"\nWorkspace DB error: {e}")

conn.close()
