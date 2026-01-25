"""
Cursor State Database Recovery Script
Attempts to recover chat history from corrupted state.vscdb
"""
import sqlite3
import os
import shutil
from datetime import datetime

CORRUPTED_PATH = r'C:\Users\admin2\AppData\Roaming\Cursor\User\globalStorage\state.vscdb.corrupted.1769226899189'
CURRENT_STATE = r'C:\Users\admin2\AppData\Roaming\Cursor\User\globalStorage\state.vscdb'
BACKUP_STATE = r'C:\Users\admin2\AppData\Roaming\Cursor\User\globalStorage\state.vscdb.backup'

def check_database(path, name):
    """Check if a database is readable and get its tables"""
    print(f"\n{'='*60}")
    print(f"Checking: {name}")
    print(f"Path: {path}")
    print(f"Size: {os.path.getsize(path) / (1024*1024):.2f} MB")
    print("="*60)
    
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables found: {len(tables)}")
        
        for t in tables[:30]:
            table_name = t[0]
            try:
                cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                count = cursor.fetchone()[0]
                print(f"  - {table_name}: {count} rows")
            except Exception as e:
                print(f"  - {table_name}: ERROR - {e}")
        
        # Check for ItemTable which typically stores state
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'")
        if cursor.fetchone():
            print("\n--- ItemTable Keys (first 50) ---")
            cursor.execute("SELECT key FROM ItemTable LIMIT 50")
            keys = cursor.fetchall()
            for k in keys:
                print(f"  {k[0][:100]}...")
        
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def attempt_recovery():
    """Attempt to recover data from corrupted database"""
    print("\n" + "="*60)
    print("ATTEMPTING RECOVERY")
    print("="*60)
    
    try:
        # Connect to corrupted database
        conn = sqlite3.connect(CORRUPTED_PATH)
        cursor = conn.cursor()
        
        # Try to export to a new clean database
        recovery_path = CORRUPTED_PATH + ".recovered.db"
        
        # Use SQLite's dump functionality
        with open(CORRUPTED_PATH + ".sql", 'w', encoding='utf-8', errors='ignore') as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
        
        print(f"SQL dump created: {CORRUPTED_PATH}.sql")
        conn.close()
        return True
        
    except Exception as e:
        print(f"Recovery failed: {e}")
        return False

def try_restore_from_corrupted():
    """Try to restore state from corrupted file"""
    print("\n" + "="*60)
    print("ATTEMPTING DIRECT RESTORE")
    print("="*60)
    
    # First verify corrupted file is actually readable
    try:
        conn = sqlite3.connect(CORRUPTED_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        print(f"Integrity check: {result}")
        
        if result == 'ok':
            print("Database passes integrity check - attempting restore...")
            # Close connection
            conn.close()
            
            # Backup current state
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{CURRENT_STATE}.pre_restore_{timestamp}"
            shutil.copy2(CURRENT_STATE, backup_path)
            print(f"Backed up current state to: {backup_path}")
            
            # Restore from corrupted
            shutil.copy2(CORRUPTED_PATH, CURRENT_STATE)
            print(f"RESTORED corrupted database as current state!")
            return True
        else:
            print(f"Database has integrity issues: {result[:200]}")
            conn.close()
            return False
            
    except Exception as e:
        print(f"Restore failed: {e}")
        return False

if __name__ == "__main__":
    print("Cursor State Database Recovery Tool")
    print(f"Run time: {datetime.now()}")
    
    # Check corrupted database
    corrupted_ok = check_database(CORRUPTED_PATH, "Corrupted Database")
    
    # Check current state
    if os.path.exists(CURRENT_STATE):
        check_database(CURRENT_STATE, "Current State Database")
    
    # Check backup
    if os.path.exists(BACKUP_STATE):
        check_database(BACKUP_STATE, "Backup State Database")
    
    # If corrupted is readable, try restore
    if corrupted_ok:
        print("\n" + "!"*60)
        print("CORRUPTED DATABASE IS READABLE!")
        print("!"*60)
        response = input("Attempt to restore from corrupted database? (yes/no): ")
        if response.lower() == 'yes':
            try_restore_from_corrupted()
