import sqlite3
import csv
import os
try:
    from database.setup_db import setup_database
except:
    from setup_db import setup_database
import sys
from flask import jsonify
import random


DB_PATH = "./database/bar_companion.db"

def create_connection():
    """Create and return a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


# bottle functions
def get_all_bottles():
    """
    Return all bottles in the database as a list of dictionaries,
    including reviews with reviewer name, score, and notes.
    """
    with create_connection() as conn:
        conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
        cursor = conn.cursor()

        # Fetch all bottles
        cursor.execute("SELECT * FROM bottles")
        bottles = cursor.fetchall()

        bottle_list = []  # List to store bottles with reviews

        for bottle in bottles:
            bottle_dict = dict(bottle)  # Convert the bottle row to a dictionary
            
            # Fetch reviews for this bottle
            cursor.execute("""
                SELECT reviews.score, reviews.notes, reviews.review_date, users.name AS reviewer_name
                FROM reviews
                JOIN users ON reviews.user_id = users.id
                WHERE reviews.bottle_id = ?
            """, (bottle["id"],))
            reviews = cursor.fetchall()

            # Add reviews to the bottle dictionary
            bottle_dict["reviews"] = [
                {
                    "reviewer_name": review["reviewer_name"],
                    "score": review["score"],
                    "notes": review["notes"],
                    "review_date": review["review_date"]
                }
                for review in reviews
            ]
            bottle_list.append(bottle_dict)

        return bottle_list

def get_random_available_bottle_id():
    with create_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query all available bottles
        cursor.execute("SELECT id FROM bottles WHERE available = 1")
        bottles = cursor.fetchall()

        if not bottles:
            return jsonify({"error": "No available bottles found"}), 404

        # Select a random bottle
        random_bottle = random.choice(bottles)
        return random_bottle

def get_bottles_from_query(query, params):
    with create_connection() as conn:
        conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
        cursor = conn.cursor()
        cursor.execute(query, params)
        bottles = cursor.fetchall()

        bottle_list = []  # List to store bottles with reviews

        for bottle in bottles:
            bottle_dict = dict(bottle)  # Convert the bottle row to a dictionary
            
            # Fetch reviews for this bottle
            cursor.execute("""
                SELECT reviews.score, reviews.notes, reviews.review_date, users.name AS reviewer_name
                FROM reviews
                JOIN users ON reviews.user_id = users.id
                WHERE reviews.bottle_id = ?
            """, (bottle["id"],))
            reviews = cursor.fetchall()

            # Add reviews to the bottle dictionary
            bottle_dict["reviews"] = [
                {
                    "reviewer_name": review["reviewer_name"],
                    "score": review["score"],
                    "notes": review["notes"],
                    "review_date": review["review_date"]
                }
                for review in reviews
            ]
            bottle_list.append(bottle_dict)

        return bottle_list
        return [dict(row) for row in bottles]
    
def get_bottle_name_by_id(bottle_id):
    """
    Retrieve the name of a bottle based on its ID.

    Parameters:
    - bottle_id (int): The ID of the bottle.

    Returns:
    - str: The name of the bottle if found, None otherwise.
    """
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM bottles WHERE id = ?", (bottle_id,))
        result = cursor.fetchone()
        if result:
            return result[0]  # Return the bottle name
        return None  # Return None if no bottle found

def add_bottle(brand, name, abv, spirit_type, subtype=None, description=None, image_path=None):
    """Add a new bottle to the database."""
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bottles (brand, name, abv, spirit_type, subtype, description, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (brand, name, abv, spirit_type, subtype, description, image_path))
        conn.commit()
    return cursor.lastrowid

def remove_bottle(bottle_id):
    """Remove a bottle from the database by its ID."""
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bottles WHERE id = ?", (bottle_id,))
        conn.commit()
    return cursor.rowcount

def update_bottle(bottle_id, **kwargs):
    """
    Update a bottle's details in the database.
    
    :param bottle_id: ID of the bottle to update.
    :param kwargs: Key-value pairs of columns and their new values.
    """
    with create_connection() as conn:
        cursor = conn.cursor()
        updates = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [bottle_id]
        cursor.execute(f"UPDATE bottles SET {updates} WHERE id = ?", values)
        conn.commit()
    return cursor.rowcount

#User functions

def get_all_users_with_reviews():
    """
    Return all users with their reviews, including the bottle name, brand, and image path, as a list of dictionaries.
    """
    with create_connection() as conn:
        conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
        cursor = conn.cursor()
        
        # Fetch all users
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        # Fetch reviews for each user and add them as an entry in the user's dictionary
        for user in users:
            user_id = user["id"]
            cursor.execute("""
                SELECT reviews.*, 
                       bottles.name AS bottle_name, 
                       bottles.brand AS bottle_brand, 
                       bottles.image_path AS bottle_image_path
                FROM reviews
                JOIN bottles ON reviews.bottle_id = bottles.id
                WHERE reviews.user_id = ?
            """, (user_id,))
            reviews = cursor.fetchall()
            user_dict = dict(user)  # Convert the user row to a dictionary
            user_dict["reviews"] = [
                {
                    **dict(review), 
                    "bottle_name": review["bottle_name"],
                    "bottle_brand": review["bottle_brand"],
                    "bottle_image_path": review["bottle_image_path"]
                } for review in reviews
            ]  # Add reviews with bottle names, brands, and image paths
            yield user_dict  # Yield each user with reviews as a dictionary

def remove_user(user_id):
    """Remove a user from the database by their ID."""
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    return cursor.rowcount


def add_user(name, image_path):
    """
    Insert a new user into the database.
    
    Parameters:
    - name (str): The name of the user.
    - image_path (str): The image path associated with the user.

    Returns:
    - user_id (int): The ID of the newly created user.
    """
    with create_connection() as conn:
        cursor = conn.cursor()
        try:
            # Insert the user into the database
            cursor.execute(
                "INSERT INTO users (name, image_path) VALUES (?, ?)",
                (name, image_path)
            )
            conn.commit()
            # Return the ID of the newly inserted user
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"An error occurred while inserting the user: {e}")
            return None

def get_user_id_by_name(name):
    """
    Retrieve the ID of a user based on their name.

    Parameters:
    - name (str): The name of the user.

    Returns:
    - int: The ID of the user if found, None otherwise.
    """
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
        result = cursor.fetchone()
        if result:
            return result[0]  # Return the user ID
        return None  # Return None if no user found
    
#Review Functions

def add_review(user_id, bottle_id, notes, score):
    """
    Insert a new review into the database.

    Parameters:
    - user_id (int): The ID of the user writing the review.
    - bottle_id (int): The ID of the bottle being reviewed.
    - notes (str): The review notes provided by the user.
    - score (int): The score given to the bottle (0-10).

    Returns:
    - review_id (int): The ID of the newly created review, or None if an error occurs.
    """
    # Validate score range
    if score not in range(0, 11):  # Ensure the score is between 0 and 10 inclusive
        print("Invalid score provided. Scores must be within 0 - 10 (inclusive).")
        return None

    with create_connection() as conn:
        cursor = conn.cursor()
        try:
            # Insert the review into the database
            cursor.execute(
                "INSERT INTO reviews (user_id, bottle_id, notes, score) VALUES (?, ?, ?, ?)",
                (user_id, bottle_id, notes, score)
            )
            conn.commit()
            # Return the ID of the newly inserted review
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"An error occurred while inserting the review: {e}")
            return None
        
def remove_review(review_id):
    """Remove a review from the database by its ID."""
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        conn.commit()
    return cursor.rowcount


def get_all_tables_contents():
    """Retrieve contents of all tables dynamically and return as a dictionary."""
    all_data = {}

    with create_connection() as conn:
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access for rows
        cursor = conn.cursor()

        # Get the list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row["name"] for row in cursor.fetchall()]

        # Fetch data from each table
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            all_data[table] = [dict(row) for row in cursor.fetchall()]

    return all_data

#--------------------------------ADMIN FUNCTIONS--------------------------------------------------------------------------

def remove_record(table, record_id):
    """
    Remove a record from a specified table by its ID.
    If the table is 'users', remove all their reviews as well.
    If the table is 'bottles', remove all reviews associated with the bottle.
    """
    with create_connection() as conn:
        cursor = conn.cursor()

        if table == "users":
            # Remove reviews associated with the user
            cursor.execute("DELETE FROM reviews WHERE user_id = ?", (record_id,))
            print(f"Removed {cursor.rowcount} reviews for user ID {record_id}.")
        
        elif table == "bottles":
            # Remove reviews associated with the bottle
            cursor.execute("DELETE FROM reviews WHERE bottle_id = ?", (record_id,))
            print(f"Removed {cursor.rowcount} reviews for bottle ID {record_id}.")

        # Remove the record from the specified table
        query = f"DELETE FROM {table} WHERE id = ?"
        cursor.execute(query, (record_id,))
        conn.commit()

    return cursor.rowcount


def delete_database():
    """Delete the existing database file."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Deleted database: {DB_PATH}")
    else:
        print(f"No database file found at: {DB_PATH}")

def insert_data_from_csv():
    CSV_FILE = './database/bottles_sample_data.csv'

    # Open the CSV file and insert rows into the database
    with open(CSV_FILE, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            add_bottle(row["brand"], row["name"], row["abv"], row["spirit_type"], row["subtype"], row["description"], row["image_path"])

    print(f"Data from {CSV_FILE} inserted into the database successfully!")

def refresh_database():
    """Refresh the database: delete, recreate, and insert data."""
    delete_database()
    setup_database()  # Function from `setup.py` to recreate the schema
    insert_data_from_csv()  # Function from `insert_data.py` to populate sample data
    print("Database refreshed successfully.")

def view_database():
        # Connect to the SQLite database
    with create_connection() as conn:
        cursor = conn.cursor()

        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables:", tables)

        # Get schema for all tables
        for table in tables:
            print(f"Schema for {table[0]}:")
            cursor.execute(f"PRAGMA table_info({table[0]});")
            print(cursor.fetchall())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        refresh_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "view":
        view_database()
    else:
        print("Usage: python db_queries.py refresh")