import sqlite3

conn = sqlite3.connect("memory.db")
cursor = conn.cursor()

print("\n--- TABLES ---")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

print("\n--- CHAT MEMORY ---")
cursor.execute("SELECT * FROM chat_memory;")
rows = cursor.fetchall()

for r in rows:
    print(r)

conn.close()