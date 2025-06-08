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
        available BOOL DEFAULT 1 CHECK (available IN (0, 1)),
        image_path TEXT
    )
    ''')

    #users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        image_path TEXT NOT NULL
    )
    ''')

    #reviews
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_id INTEGER,
        bottle_id INTEGER NOT NULL,
        review_text TEXT,
        score INTEGER,
        review_date DATE DEFAULT CURRENT_DATE,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (bottle_id) REFERENCES bottles(id),
        FOREIGN KEY (event_id) REFERENCES events(id)          
    )
    ''')

    #nights
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folder_path TEXT,
        name TEXT NOT NULL,
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
    
    #records of bottle notes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS community_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            tasting_note_id INTEGER NOT NULL,
            FOREIGN KEY (review_id) REFERENCES reviews(id),
            FOREIGN KEY (tasting_note_id) REFERENCES tasting_notes(id)
        )
        ''')
    
    #records of expert bottle notes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expert_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bottle_id INTEGER NOT NULL,
            tasting_note_id INTEGER NOT NULL,
            FOREIGN KEY (tasting_note_id) REFERENCES tasting_notes(id),
            FOREIGN KEY (bottle_id) REFERENCES bottles(id)
        )
        ''')
    
    #Tasting Notes master table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasting_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT,
            parent TEXT,
            tier TEXT NOT NULL
        )
        ''')
    
    #name, parent, tier
    tasting_data = [
        ("Fruity", None, 3),
        ("cooked fruit", "Fruity", 2),
        ("marmalade", "cooked fruit", 1),
        ("jam", "cooked fruit", 1),
        ("apple pie", "cooked fruit", 1),
        ("Berry", "Fruity", 2),
        ("Raspberry", "Berry", 1),
        ("Blackberry", "Berry", 1),
        ("Blueberry", "Berry", 1),
        ("strawberry", "Berry", 1),
        ("tropical", "Fruity", 2),
        ("Orange", "tropical", 1),
        ("Lemon", "tropical", 1),
        ("Orange Peel", "tropical", 1),
        ("coconut", "tropical", 1),
        ("banana", "tropical", 1),
        ("stone fruit", "Fruity", 2),
        ("plum", "stone fruit", 1),
        ("peach", "stone fruit", 1),
        ("cherry", "stone fruit", 1),
        ("apricot", "stone fruit", 1),
        ("fruit", "Fruity", 2),
        ("raisin", "fruit", 1),
        ("grape", "fruit", 1),
        ("fig", "fruit", 1),
        ("apple", "fruit", 1),
        ("Spice", None, 3),
        ("baking spice", "Spice", 2),
        ("Nutmeg", "baking spice", 1),
        ("clove", "baking spice", 1),
        ("coriander", "baking spice", 1),
        ("cinnamon", "baking spice", 1),
        ("staranise", "baking spice", 1),
        ("Savory spice", "Spice", 2),
        ("white pepper", "Savory spice", 1),
        ("spearmint", "Savory spice", 1),
        ("herbal", "Savory spice", 1),
        ("fennel", "Savory spice", 1),
        ("dill", "Savory spice", 1),
        ("black pepper", "Savory spice", 1),

        ("Sweet", None, 3),
        ("vanillas", "Sweet", 2),
        ("vanilla", "vanillas", 1),
        ("custard", "vanillas", 1),
        ("creme brulee", "vanillas", 1),
        ("soda", "Sweet", 2),
        ("cherry soda", "soda", 1),
        ("creme soda", "soda", 1),
        ("root beer", "soda", 1),
        ("cola", "soda", 1),
        ("Dessert", "Sweet", 2),
        ("brown sugar", "Dessert", 1),
        ("butterscotch", "Dessert", 1),
        ("caramel", "Dessert", 1),
        ("graham cracker", "Dessert", 1),
        ("honey", "Dessert", 1),
        ("licorice", "Dessert", 1),
        ("maple syrup", "Dessert", 1),
        ("marshmellow", "Dessert", 1),
        ("molasses", "Dessert", 1),
        ("toffee", "Dessert", 1),
        ("chocolates", "Sweet", 2),
        ("bitter chocolate", "chocolates", 1),
        ("milk chocolate", "chocolates", 1),
        ("chocolate mocha", "chocolates", 1),
        ("chocolate milk", "chocolates", 1),
        
        ("Grain", None, 3),
        ("corn", "Grain", 2),
        ("corn", "corn", 1),
        ("malt", "Grain", 2),
        ("cereal", "malt", 1),
        ("cocoa", "malt", 1),
        ("rye", "Grain", 2),
        ("rye", "rye", 1),
        ("bread", "Grain", 2),
        ("bread", "bread", 1),
        ("buckwheat pancakes", "bread", 1),
        
        ("Wood", None, 3),
        ("oak", "Wood", 2),
        ("smoky oak", "oak", 1),
        ("sweet oak", "oak", 1),
        ("toasted oak", "oak", 1),
        ("pine", "Wood", 2),
        ("cedar", "pine", 1),
        ("pine", "pine", 1),
        ("Nut", "Wood", 2),
        ("almond", "Nut", 1),
        ("hazelnut", "Nut", 1),
        ("peanut", "Nut", 1),
        ("pecan", "Nut", 1),
        ("walnut", "Nut", 1),
        ("Earthy", "Wood", 2),
        ("coffee", "Earthy", 1),
        ("leather", "Earthy", 1),
        ("tobacco", "Earthy", 1),
        ("peat", "Earthy", 1),
        ("smoke", "Earthy", 1),

        ("Floral", None, 3),
        ("Floral", "Floral", 2),
        ("Rose", "Floral", 1),
        ("Heather", "Floral", 1),
        ("Violet", "Floral", 1),
    ]

    cursor.executemany('''
    INSERT INTO tasting_notes (name, parent, tier)
    VALUES (?, ?, ?)
''', tasting_data)

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    print("Database and tables created successfully!")
