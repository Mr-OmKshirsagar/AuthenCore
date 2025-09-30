import sqlite3

def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns

def main():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Create users table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ensure username column exists in users
    if not column_exists(cursor, "users", "username"):
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        print("✅ Added 'username' column to users")

    # Ensure email column exists in users
    if not column_exists(cursor, "users", "email"):
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
        print("✅ Added 'email' column to users")

    # Create admin table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert default admin if none exists
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)",
                       ("admin", "admin123"))
        print("✅ Default admin account created: username='admin', password='admin123'")

    conn.commit()
    conn.close()
    print("🎉 Database fix complete! You can now log in with user or admin.")

if __name__ == "__main__":
    main()
