import sqlite3

def setup_database():
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect('./database/bar_companion.db')

    # Create a cursor object
    cursor = conn.cursor()

    # Create the "bottles" table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bottles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        name TEXT NOT NULL,
        abv TEXT NOT NULL,
        spirit_type TEXT NOT NULL,
        subtype TEXT,
        description TEXT,
        isempty BOOL DEFAULT 0 CHECK (isempty IN (0, 1)),
        image_path TEXT
    )
    ''')

    #users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        image_path DATE NOT NULL
    )
    ''')

    #reviews
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        night_id INTEGER,
        bottle_id INTEGER NOT NULL,
        notes TEXT,
        score INTEGER,
        review_date DATE DEFAULT CURRENT_DATE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (bottle_id) REFERENCES bottles(id),
        FOREIGN KEY (night_id) REFERENCES nights(id)          
    )
    ''')

    #nights
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_path TEXT,
        code TEXT NOT NULL,
        event_date DATE DEFAULT CURRENT_DATE
    )
    ''')

    #event participants
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS event_participants(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (event_id) REFERENCES events(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    #event drinks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_drinks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            bottle_id INTEGER NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (bottle_id) REFERENCES bottles(id)
        )
        ''')

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    print("Database and tables created successfully!")
