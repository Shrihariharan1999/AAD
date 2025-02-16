import sqlite3

def inspect_database(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Connected to the database.")

    # Fetch all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("\nTables in the database:")
    for table in tables:
        print(f"- {table[0]}")

        # Fetch and display the contents of each table
        cursor.execute(f"SELECT * FROM {table[0]}")
        rows = cursor.fetchall()

        # Fetch column names
        cursor.execute(f"PRAGMA table_info({table[0]});")
        columns = [col[1] for col in cursor.fetchall()]

        print(f"  Columns: {', '.join(columns)}")
        print("  Rows:")
        for row in rows:
            print(f"    {row}")
        print()

    # Close the connection
    conn.close()
    print("Database inspection complete.")

# Specify the path to your SQLite database
database_path = "college.db"  # Replace with the path to your database
inspect_database(database_path)
