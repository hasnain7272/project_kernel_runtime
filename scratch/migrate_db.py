import sqlite3
import os

db_path = "app.db" # Standard name
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN tool_calls TEXT")
        conn.commit()
        print("Schema updated successfully (tool_calls added).")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column tool_calls already exists.")
        else:
            print(f"Error updating schema: {e}")
    finally:
        conn.close()
else:
    print(f"Database not found at {db_path}")
