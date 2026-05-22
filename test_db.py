import sqlite3

conn = sqlite3.connect("glycemia.db")

cursor = conn.cursor()

cursor.execute("SELECT * FROM users")

print(cursor.fetchall())

conn.close()