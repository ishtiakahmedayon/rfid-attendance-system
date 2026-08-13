"""
Helper for manually managing Admins.password entries -- this script
never touches the database. You generate a hash here, then INSERT it
into the Admins table yourself (via a DB browser, sqlite3 CLI, etc).

Usage:
    python admin_password_tool.py hash <plaintext-password>
        Prints a hash suitable for pasting straight into Admins.password.

    python admin_password_tool.py check <plaintext-password> <stored-hash>
        Prints MATCH or NO MATCH -- useful for confirming a hash you
        already have in the DB actually corresponds to the password you
        think it does, without needing to log in to test it.

Example:
    python admin_password_tool.py hash "correct horse battery staple"
    -> pbkdf2:sha256:600000$....

    Then in the DB:
    INSERT INTO Admins (username, password) VALUES ('yourname', '<paste hash>');
"""

import sys

from werkzeug.security import check_password_hash, generate_password_hash


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "hash":
        password = sys.argv[2]
        print(generate_password_hash(password))

    elif command == "check":
        if len(sys.argv) < 4:
            print("Usage: python admin_password_tool.py check <password> <hash>")
            sys.exit(1)
        password = sys.argv[2]
        stored_hash = sys.argv[3]
        print("MATCH" if check_password_hash(stored_hash, password) else "NO MATCH")

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()