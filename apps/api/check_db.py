import sqlite3

conn = sqlite3.connect("upsc.db")
c = conn.cursor()

# List tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("=== Tables ===")
for t in tables:
    name = t[0]
    count = c.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
    print(f"  {name}: {count} rows")

# Check users
print("\n=== Users ===")
try:
    for row in c.execute("SELECT id, email, full_name FROM users"):
        print(f"  {row}")
except:
    print("  No users table or empty")

# Check documents
print("\n=== Documents ===")
try:
    for row in c.execute("SELECT id, original_filename, status FROM documents"):
        print(f"  {row}")
except:
    print("  No documents table or empty")

conn.close()
