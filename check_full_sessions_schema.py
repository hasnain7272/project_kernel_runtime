import sqlite3
conn = sqlite3.connect('kernel.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(sessions)")
schema = cursor.fetchall()
print('Full sessions table schema:')
for col in schema:
    print(f'  {col[0]}: {col[1]} {col[2]} {"NOT NULL" if col[3] else "NULL"} (default: {col[4]}) (pk: {col[5]})')
conn.close()