import sqlite3
import os

corrupted = r'C:\Users\admin2\AppData\Roaming\Cursor\User\globalStorage\state.vscdb.corrupted.1769226899189'
current = r'C:\Users\admin2\AppData\Roaming\Cursor\User\globalStorage\state.vscdb'

print('=== CORRUPTED DATABASE ===')
print(f'Size: {os.path.getsize(corrupted) / (1024*1024*1024):.2f} GB')
try:
    conn = sqlite3.connect(corrupted)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f'Tables: {len(tables)}')
    for t in tables[:15]:
        print(f'  {t[0]}')
    conn.close()
    print('STATUS: READABLE')
except Exception as e:
    print(f'Error: {e}')

print()
print('=== CURRENT DATABASE ===')
print(f'Size: {os.path.getsize(current) / (1024*1024):.2f} MB')
try:
    conn = sqlite3.connect(current)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    print(f'Tables: {len(tables)}')
    for t in tables[:15]:
        print(f'  {t[0]}')
    conn.close()
except Exception as e:
    print(f'Error: {e}')
