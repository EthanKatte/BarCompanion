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
                SELECT reviews.id, reviews.score, reviews.review_text, reviews.review_date, users.name AS reviewer_name
                FROM reviews
                JOIN users ON reviews.user_id = users.id
                WHERE reviews.bottle_id = ?
            """, (bottle["id"],))
            reviews = cursor.fetchall()

            bottle_dict["tasting_notes"] = get_tasting_notes_by_bottle_id(bottle["id"])
            bottle_dict["expert_tasting_notes"] = get_expert_tasting_notes_for_bottle(bottle["id"])

            # Add reviews to the bottle dictionary
            bottle_dict["reviews"] = [
                {
                    "reviewer_name": review["reviewer_name"],
                    "score": review["score"],
                    "review_text": review["review_text"],
                    "review_date": review["review_date"],
                    "tasting_notes": get_tasting_notes_by_review(review["id"])
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
                SELECT reviews.id, reviews.score, reviews.review_text, reviews.review_date, users.name AS reviewer_name
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
                    "notes": review["review_text"],
                    "review_date": review["review_date"],
                    "tasting_notes": get_tasting_notes_by_review(review["id"])
                }
                for review in reviews
            ]
            bottle_list.append(bottle_dict)

        return bottle_list
    
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
        ''', (brand, name, abv, spirit_type.capitalize(), subtype, description, image_path))
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
                    "bottle_image_path": review["bottle_image_path"],
                    "tasting_notes": get_tasting_notes_by_review(review["id"])
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
        name = name.capitalize()
        try:
            # Insert the user into the database
            cursor.execute(
                "INSERT INTO users (name, image_path) VALUES (?, ?)",
                (name.capitalize(), image_path)
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
        cursor.execute("SELECT id FROM users WHERE name = ?", (name.capitalize(),))
        result = cursor.fetchone()
        if result:
            return result[0]  # Return the user ID
        return None  # Return None if no user found
    
#Review Functions

def add_review(user_id, bottle_id, notes, score, event_id=None):
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
                "INSERT INTO reviews (user_id, bottle_id, review_text, score, event_id) VALUES (?, ?, ?, ?, ?)",
                (user_id, bottle_id, notes, score, event_id)
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

#Event functions

def get_all_events():
    """
    Retrieve all events from the database, including their bottles and participants.

    :return: A list of events, each with a bottles list and participants list.
    """
    events = []
    with create_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all events
        cursor.execute("SELECT * FROM events")
        events_data = cursor.fetchall()
        

        for event in events_data:
            event_id = event["id"]

            # Get bottles for the event
            cursor.execute("""
                SELECT bottles.*
                FROM event_drinks
                JOIN bottles ON event_drinks.bottle_id = bottles.id
                WHERE event_drinks.event_id = ?
            """, (event_id,))
            bottles = [dict(row) for row in cursor.fetchall()]

            # Get participants for the event
            cursor.execute("""
                SELECT users.*
                FROM event_participants
                JOIN users ON event_participants.user_id = users.id
                WHERE event_participants.event_id = ?
            """, (event_id,))
            participants = [dict(row) for row in cursor.fetchall()]

            # Add event with bottles and participants to the list
            events.append({
                "id": event["id"],
                "folder_path": event["folder_path"],
                "code": event["code"],
                "name": event["name"],
                "event_date": event["event_date"],
                "bottles": bottles,
                "users": participants,
            })
    return events

def add_event(code, event_date, folder_path, name):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (code, event_date, folder_path, name)
            VALUES (?, ?, ?, ?)
        """, (code, event_date, folder_path, name))
        conn.commit()
    return cursor.rowcount

def get_event_by_id(event_id):
    """
    Retrieve an event by its ID, including associated participants and bottles.

    :param event_id: The ID of the event to retrieve.
    :return: A dictionary with event details, participants, and bottles.
    """
    try:
        with create_connection() as conn:
            conn.row_factory = sqlite3.Row  # Enable dictionary-like row access
            cursor = conn.cursor()

            # Query to fetch the event details
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            event = cursor.fetchone()

            if not event:
                return None  # Event not found

            # Query to fetch participants for the event
            cursor.execute("""
                SELECT users.*
                FROM event_participants
                JOIN users ON event_participants.user_id = users.id
                WHERE event_participants.event_id = ?
            """, (event_id,))
            participants = [dict(row) for row in cursor.fetchall()]
            for participant in participants:
                cursor.execute("""
                    SELECT *
                    FROM reviews
                    WHERE user_id = ? AND event_id = ?
                """, (participant["id"], event_id))

                participant["reviews"] = [dict(row) for row in cursor.fetchall()]
                for review in participant["reviews"]:
                    review["tasting_notes"] = get_tasting_notes_by_review(review["id"])
                #for review in participant["reviews"]:
                #    print("review, ", review.keys())
                #    print("bottle_id, ", type(review["bottle_id"]))
                #    cursor.execute("""
                #        SELECT *
                #        FROM bottles
                #        WHERE id = ?
                #    """, (review["bottle_id"]))
                #    review["bottle"] = cursor.fetchone()



            # Query to fetch bottles for the event
            cursor.execute("""
                SELECT bottles.*
                FROM event_drinks
                JOIN bottles ON event_drinks.bottle_id = bottles.id
                WHERE event_drinks.event_id = ?
            """, (event_id,))
            bottles = [dict(row) for row in cursor.fetchall()]
            for bottle in bottles:
                cursor.execute("""
                    SELECT reviews.*, users.name AS reviewer_name
                    FROM reviews
                    JOIN users ON reviews.user_id = users.id
                    WHERE bottle_id = ? AND event_id = ?
                """, (bottle["id"], event_id))

                bottle["reviews"] = [dict(row) for row in cursor.fetchall()]

            # Return the event details along with participants and bottles
            return {
                "id": event["id"],
                "name": event["name"],
                "folder_path": event["folder_path"],
                "event_date": event["event_date"],
                "users": participants,
                "bottles": bottles,
            }
    except Exception as e:
        print(f"Error retrieving event by ID: {e}")
        return None
    
def add_bottle_to_event(bottle_ids, event_id):
    with create_connection() as conn:
        cursor = conn.cursor()
        for bottle_id in bottle_ids:
            cursor.execute("""
                INSERT INTO event_drinks (event_id, bottle_id)
                VALUES (?, ?)
            """, (event_id, bottle_id))
        conn.commit()
    return jsonify({"message": "Bottles added successfully"}), 200

def add_user_to_event(user_ids, event_id):
    """
    Add users to an event by inserting records into the event_participants table.

    :param user_ids: List of user IDs to add to the event.
    :param event_id: ID of the event.
    :return: A JSON response indicating success or failure.
    """
    with create_connection() as conn:
        cursor = conn.cursor()
        for user_id in user_ids:
            cursor.execute("""
                INSERT INTO event_participants (event_id, user_id)
                VALUES (?, ?)
            """, (event_id, user_id))
        conn.commit()
    return jsonify({"message": "Users added successfully"}), 200

# Tasting note functions

def get_tasting_notes():
    """Retrieve all tasting notes and structure them as a list of dictionaries for Jinja template."""
    structured_notes = []

    with sqlite3.connect('./database/bar_companion.db') as conn:
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access for rows
        cursor = conn.cursor()

        # Fetch all tasting notes from the database based on their tier
        cursor.execute("SELECT * FROM tasting_notes WHERE tier = 3")
        generic_rows = cursor.fetchall()  # Tier 3 (Top-level notes)

        cursor.execute("SELECT * FROM tasting_notes WHERE tier = 2")
        intermediate_rows = cursor.fetchall()  # Tier 2 (Subgroup notes)

        cursor.execute("SELECT * FROM tasting_notes WHERE tier = 1")
        specific_rows = cursor.fetchall()  # Tier 1 (Subsubgroup notes)

        # Build the hierarchical structure of notes
        for generic_row in generic_rows:
            note = {
                "name": generic_row["name"],
                "parent": generic_row["parent"],
                "subnotes": []
            }

            # Add subnotes (tier 2) under each top-level note (tier 3)
            for intermediate_row in intermediate_rows:
                if intermediate_row["parent"] == generic_row["name"]:
                    subnote = {
                        "name": intermediate_row["name"],
                        "subsubnotes": []
                    }

                    # Add subsubnotes (tier 1) under each subnote (tier 2)
                    for specific_row in specific_rows:
                        if specific_row["parent"] == intermediate_row["name"]:
                            subnote["subsubnotes"].append(specific_row["name"])

                    note["subnotes"].append(subnote)

            # Append the note with its subnotes and subsubnotes to the structured list
            structured_notes.append(note)

    return structured_notes

def get_tasting_note_id(note_name):
    """
    Retrieves the ID of a tasting note from its name.

    Parameters:
    - note_name (str): The name of the tasting note.

    Returns:
    - int: The ID of the tasting note, or None if the note is not found.
    """
    try:
        # Establish database connection
        with create_connection() as conn:
            cursor = conn.cursor()
            
            # Query to retrieve the ID of the tasting note by its name
            cursor.execute("SELECT id FROM tasting_notes WHERE name = ?", (note_name,))
            result = cursor.fetchone()
            
            # Return the ID if found, otherwise return None
            if result:
                return result[0]
            else:
                return None  # If no matching note is found
    except sqlite3.Error as e:
        print(f"An error occurred while retrieving the tasting note ID: {e}")
        return None
    
def add_note_record(review_id, tasting_note_id):
    """
    Adds a new entry to the note_records table.

    Parameters:
    - review_id (int): The ID of the review to associate the note with.
    - tasting_note_id (int): The ID of the tasting note to be associated with the review.
    
    Returns:
    - bool: True if the entry was added successfully, False if there was an error.
    """
    try:
        # Establish database connection
        with create_connection() as conn:
            cursor = conn.cursor()
            
            # Insert the new entry into the note_records table
            cursor.execute(
                "INSERT INTO community_notes (review_id, tasting_note_id) VALUES (?, ?)",
                (review_id, tasting_note_id)
            )
            
            # Commit the changes
            conn.commit()
            
            # Return True if the insert was successful
            return True
    except sqlite3.Error as e:
        print(f"An error occurred while adding the note record: {e}")
        return False
    
def get_tasting_notes_by_bottle_id(bottle_id):
    """
    Retrieves the count of each tasting note found in reviews of a given bottle.

    Parameters:
    - bottle_id (int): The ID of the bottle.
    - db_connection (sqlite3.Connection): The SQLite database connection.

    Returns:
    - list of tuples: Each tuple contains the tasting note name and its count.
    """
    query = """
    SELECT tn.name, COUNT(*) AS note_count
    FROM reviews r
    JOIN community_notes nr ON r.id = nr.review_id
    JOIN tasting_notes tn ON nr.tasting_note_id = tn.id
    WHERE r.bottle_id = ?
    GROUP BY tn.name
    ORDER BY note_count DESC;
    """


    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (bottle_id,))
        result = cursor.fetchall()
    
    return result

def get_tasting_notes_by_review(review_id):
    """
    Retrieves the tasting notes for a given review.

    Parameters:
    - review_id (int): The ID of the review.
    - db_connection (sqlite3.Connection): The SQLite database connection.

    Returns:
    - list of strings: The names of the tasting notes for the review.
    """
    query = """
    SELECT tn.name
    FROM community_notes nr
    JOIN tasting_notes tn ON nr.tasting_note_id = tn.id
    WHERE nr.review_id = ?;
    """
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (review_id,))
        result = cursor.fetchall()

    return [row[0] for row in result]

#expert note functions

def update_expert_notes(bottle_id, tasting_note_ids):
    """
    Updates the expert notes for a given bottle ID by removing existing notes
    and inserting new ones.

    :param bottle_id: The ID of the bottle to update notes for.
    :param tasting_note_ids: A list of tasting note IDs to associate with the bottle.
    """
    try:
        # Connect to the SQLite database
        with create_connection() as conn:
            cursor = conn.cursor()

            # Begin a transaction
            conn.execute("BEGIN TRANSACTION;")

            # Delete all existing notes for the given bottle ID
            cursor.execute('''
                DELETE FROM expert_notes
                WHERE bottle_id = ?
            ''', (bottle_id,))

            # Insert the new tasting notes for the bottle
            cursor.executemany('''
                INSERT INTO expert_notes (bottle_id, tasting_note_id)
                VALUES (?, ?)
            ''', [(bottle_id, note_id) for note_id in tasting_note_ids])


    except sqlite3.Error as e:
        # Rollback in case of an error
        conn.rollback()
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        conn.close()

def update_bottle_description(bottle_id, description):
    """
    Updates the description of a bottle in the database.

    :param bottle_id: The ID of the bottle to update.
    :param description: The new description for the bottle.
    """
    try:
        # Connect to the SQLite database
        with create_connection() as conn:
            cursor = conn.cursor()

            # Update the bottle description
            cursor.execute('''
                UPDATE bottles
                SET description = ?
                WHERE id = ?
            ''', (description, bottle_id))

            print(f"Description for bottle_id {bottle_id} updated successfully.")

    except sqlite3.Error as e:
        # Handle errors
        print(f"An error occurred: {e}")

def bottle_exists(brand, name):
    """
    Check if a brand-name pair exists in the bottles table.

    :param brand: The brand of the bottle to check.
    :param name: The name of the bottle to check.
    :return: True if the brand-name pair exists, otherwise False.
    """
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM bottles WHERE brand = ? AND name = ? LIMIT 1", (brand, name)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"An error occurred while checking the bottle: {e}")
        return False
    
def user_exists(name):
    """
    Check if a name exists in the users table.

    :param name: The name of the user to check.
    :param connection: SQLite connection object.
    :return: True if the user exists, otherwise False.
    """
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM users WHERE name = ? LIMIT 1", (name,)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"An error occurred while checking the user: {e}")
        return False
    
def get_expert_tasting_notes_for_bottle(bottle_id):
    """
    Given a bottle_id, returns a list of tasting notes (as names) associated with it.

    Args:
        bottle_id (int): The ID of the bottle.

    Returns:
        list: A list of tasting note names.
    """
    tasting_notes = []
    query = '''
        SELECT tn.name
        FROM expert_notes en
        JOIN tasting_notes tn ON en.tasting_note_id = tn.id
        WHERE en.bottle_id = ?
    '''

    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (bottle_id,))
        rows = cursor.fetchall()
        
        tasting_notes = [row[0] for row in rows]

    return tasting_notes

def get_event_participants(event_id):
    """
    Fetches all participants for a given event ID from the database.

    Args:
        event_id (int): The ID of the event.

    Returns:
        list: A list of dictionaries, where each dictionary represents a participant with their details.
    """
    query = """
    SELECT users.id, users.name, users.image_path
    FROM event_participants
    INNER JOIN users ON event_participants.user_id = users.id
    WHERE event_participants.event_id = ?
    """

    # Use create_connection() to connect to the database
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, (event_id,))
        rows = cursor.fetchall()

    # Map results to a list of dictionaries for better readability
    participants = [
        {"id": row[0], "name": row[1], "image_path": row[2]} for row in rows
    ]

    return participants


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

import os
import pandas as pd
from datetime import datetime

def backup_database():
    """
    Backs up all tables in the bar_companion.db database to separate CSV files
    in a directory named ./database_backup/{today's date}.
    """
    # Database and backup directory
    database_path = "./database/bar_companion.db"
    backup_dir = f"./database_backup/{datetime.now().strftime('%Y-%m-%d')}"

    # Create the backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)

    # Connect to the database
    with sqlite3.connect(database_path) as conn:
        cursor = conn.cursor()

        # Get a list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        # Export each table to a CSV file
        for table in tables:
            # Query all data from the table
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)

            # Save to CSV in the backup directory
            csv_path = os.path.join(backup_dir, f"{table}.csv")
            df.to_csv(csv_path, index=False)

    print(f"Database backup completed. Files saved in: {backup_dir}")

def load_csvs(folder_path):
    """
    Recreates the database schema and loads all CSV files from a given folder
    into the bar_companion.db database. Each CSV file should be named
    after the table it belongs to.

    Args:
        folder_path (str): Path to the folder containing the CSV files.
    """
    database_path = "./database/bar_companion.db"

    # Step 1: Recreate the database schema
    delete_database()
    setup_database()
    print("Database schema recreated.")

    # Step 2: Load CSV data into the database
    with sqlite3.connect(database_path) as conn:
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".csv"):
                table_name = os.path.splitext(file_name)[0]
                file_path = os.path.join(folder_path, file_name)

                # Read the CSV into a DataFrame
                df = pd.read_csv(file_path)

                # Ensure the 'id' column is properly handled
                if 'id' in df.columns:
                    df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)

                # Load DataFrame into the database
                df.to_sql(table_name, conn, if_exists="append", index=False)

                print(f"Loaded {file_name} into table {table_name}.")
    
    print("All CSV files have been loaded into the database.")



if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        refresh_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "view":
        view_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "backup":
        backup_database()
    elif len(sys.argv) > 2 and sys.argv[1] == "load":
        load_csvs(sys.argv[2])
        #add_bottle("test", "test", "test", "test")
        #nones = [x for x in get_all_bottles() if not x["id"]]
        #print(get_all_bottles())
        #print(nones)
    else:
        print("INCORRECT USAGE OF THE ADMIN COMMANDS")