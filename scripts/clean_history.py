import shutil
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / 'users.db'
BACKUP = DB.with_suffix('.db.bak')

print(f'Using DB: {DB}')
if not DB.exists():
    print('Database not found. Exiting.')
    exit(1)

# Backup
shutil.copy2(DB, BACKUP)
print(f'Backup created at: {BACKUP}')

conn = sqlite3.connect(DB)
c = conn.cursor()

# Count truncated rows
c.execute("SELECT COUNT(*) FROM history WHERE action LIKE '%...'")
count = c.fetchone()[0]
print(f'Found {count} truncated history rows (actions containing "...").')

if count == 0:
    print('Nothing to delete.')
    conn.close()
    exit(0)

# Delete truncated rows
c.execute("DELETE FROM history WHERE action LIKE '%...'")
conn.commit()

# Verify
c.execute("SELECT COUNT(*) FROM history WHERE action LIKE '%...'")
remaining = c.fetchone()[0]
conn.close()
print(f'Deletion complete. Remaining truncated rows: {remaining}')
print('If you want to undo, restore the backup file users.db.bak')
