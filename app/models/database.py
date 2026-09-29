import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'database.db')

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # users table is straightforward
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # interactions table with schema that may grow over time
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            product_id INTEGER,
            interaction_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # orders table to store placed orders and shipping address
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            items TEXT,
            total REAL,
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            country TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # saved addresses for user profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            label TEXT,
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            country TEXT,
            is_default INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # If the table already existed from an older release, make sure the
    # new columns are present.  SQLite doesn't modify an existing table
    # when running CREATE TABLE IF NOT EXISTS, so we query the table
    # info and alter if necessary.
    cursor.execute("PRAGMA table_info(interactions)")
    existing_cols = {row[1] for row in cursor.fetchall()}  # name column
    if "interaction_type" not in existing_cols:
        try:
            cursor.execute("ALTER TABLE interactions ADD COLUMN interaction_type TEXT")
        except sqlite3.OperationalError:
            pass
    if "timestamp" not in existing_cols:
        try:
            cursor.execute("ALTER TABLE interactions ADD COLUMN timestamp DATETIME")
        except sqlite3.OperationalError:
            pass

    # Ensure orders table has payment columns for newer releases
    cursor.execute("PRAGMA table_info(orders)")
    order_cols = {row[1] for row in cursor.fetchall()}
    if "payment_method" not in order_cols:
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT")
        except sqlite3.OperationalError:
            pass
    if "payment_status" not in order_cols:
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

# Initialize on import
init_db()