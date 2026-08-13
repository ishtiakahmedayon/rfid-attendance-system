"""
One-time migration: creates the Admins table for the admin dashboard.

No seeding happens here -- admin accounts are inserted manually. Use
admin_password_tool.py to generate a password hash first:

    python admin_password_tool.py hash "your-password"

then insert the row yourself, e.g. via the sqlite3 CLI:

    INSERT INTO Admins (username, password) VALUES ('yourname', '<paste hash>');

Once at least one admin exists, that account can create further admins
directly from the admin dashboard (Admins is one of the manageable
entities) -- the dashboard hashes the password for you at that point,
so admin_password_tool.py is really only needed to bootstrap the very
first account.

Run once: python create_admins_table.py
"""

from database import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS Admins (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    """
)

conn.commit()
conn.close()

print("Admins table is ready. Insert your first admin manually -- see the")
print("instructions at the top of this file, or run:")
print('  python admin_password_tool.py hash "your-password"')