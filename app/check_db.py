import sqlite3

conn = sqlite3.connect('barberia.db')
cur = conn.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("TABLES:", tables)

for t in tables:
    tname = t[0]
    cols = cur.execute(f"PRAGMA table_info({tname})").fetchall()
    print(f"\n--- {tname} ---")
    for c in cols:
        print(c)

conn.close()
