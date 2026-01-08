import sqlite3
conn = sqlite3.connect('/app/data/mindex.db')
c = conn.cursor()
c.execute("DELETE FROM species WHERE kingdom != 'Fungi' OR kingdom IS NULL")
print(f'Deleted {c.rowcount} non-fungi species')
conn.commit()
c.execute("SELECT kingdom, COUNT(*) FROM species GROUP BY kingdom")
print('Remaining:', dict(c.fetchall()))
conn.close()