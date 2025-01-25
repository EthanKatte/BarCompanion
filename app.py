from flask import Flask, render_template, request, jsonify, redirect
from database.db_queries import (get_all_bottles, 
                                add_bottle, 
                                remove_bottle, 
                                get_bottles_from_query, 
                                get_all_users_with_reviews, 
                                add_user, 
                                get_user_id_by_name,
                                add_review,
                                get_all_tables_contents, 
                                remove_record,
                                get_random_available_bottle_id,
                                update_bottle,
                                get_all_events,
                                add_event,
                                get_event_by_id,
                                add_bottle_to_event,
                                add_user_to_event,
                                get_tasting_notes,
                                add_note_record,
                                get_tasting_note_id,
                                get_tasting_notes_by_bottle_id,
                                get_tasting_notes_by_review,
                                update_expert_notes,
                                update_bottle_description,
                                bottle_exists,
                                user_exists,
                                get_event_participants
                                )
from flask_cors import CORS
import base64
import os

app = Flask(__name__)
CORS(app)

@app.route('/', methods=["GET"])
def johns_bar():
    return render_template('johns_bar.html')

@app.route('/home', methods=["GET"])
def home():
    return render_template('home.html')

@app.route('/inventory', methods=["GET"])
def inventory():
    # Example data to pass to the inventory page
    if len(request.args) == 0:
        bottles = get_all_bottles()
        tasting_notes = get_tasting_notes()
        users = list(get_all_users_with_reviews())
        print(bottles)
        return render_template('inventory.html', bottles=bottles, tasting_notes=tasting_notes, users=users)

    filters = {
        "brand": request.args.get("brand"),
        "spirit_type": request.args.get("type"),
        "subtype": request.args.get("subtype"),
    }
    sort_by = request.args.get("sort_by", "name")  # Default sort by name
    order = request.args.get("order", "asc")  # Default order is ascending

    # Build SQL query dynamically based on filters
    query = "SELECT * FROM bottles WHERE 1=1"
    params = []
    for key, value in filters.items():
        if value:
            query += f" AND {key} = ?"
            params.append(value)

    query += f" ORDER BY {sort_by} {order.upper()}"  # Add sorting
    bottles = get_bottles_from_query(query, params)
    tasting_notes = get_tasting_notes()
    users = get_all_users_with_reviews()
    return render_template('inventory.html', bottles=bottles, tasting_notes=tasting_notes, users=users)

@app.route('/users', methods=["GET"])
def users():
    users = get_all_users_with_reviews()
    return render_template('users.html', users=users)

@app.route("/events", methods=["GET"])
def events():
    try:
        events = get_all_events()  # Call the database function
        return render_template('events.html', events=events)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/event", methods=["GET"])
def event():
    id = request.args.get('id')
    version = request.args.get('version')

    if version == "client":
        event = get_event_by_id(id)
        return render_template("event_client_login.html", event=event)
    elif version == "console":
        event=get_event_by_id(id)
        bottles = get_all_bottles()
        users = get_all_users_with_reviews()
        print(event)

            # Fetch all image files in the directory
        try:
            images = [
                f"{event['folder_path']}/{file}" for file in os.listdir(event['folder_path']) if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
            ]
        except FileNotFoundError:
            images = []  # If the folder doesn't exist, return an empty list



        if not event:
            return "An error occurred: unknown event provided."
        return render_template("event_console.html", event=event, bottles=bottles, users=list(users), images=images)
    else:
        return "An error occurred: unknown URL version provided. Options are client/console.", 500

@app.route("/event_client", methods=["GET"])
def event_client():
    id = request.args.get('id')
    user_id = request.cookies.get("user_id")
    tasting_notes = get_tasting_notes()
    if user_id:
        event = get_event_by_id(id)
        user = [u for u in list(get_all_users_with_reviews()) if u["id"] == int(user_id)][0]
        print([participant["id"] for participant in get_event_participants(id)])
        print(user_id)
        if int(user_id) not in [int(participant["id"]) for participant in get_event_participants(id)]:
            add_user_to_event([user_id], id)
        return render_template("event_client.html", event=event, user=user, tasting_notes=tasting_notes)
    else:
        return jsonify({"error": "User ID cookie not found"}), 404


@app.route('/fuckoff', methods=["GET"])
def admin_page():
    print(get_tasting_notes())
    try:
        tables_data = get_all_tables_contents()
        return render_template("admin.html", tables_data=tables_data)
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

@app.route("/expert_notes", methods=["GET"])
def expert_notes():
    tasting_notes = get_tasting_notes()
    bottles = get_all_bottles()

    return render_template("expert_notes.html", bottles=bottles, tasting_notes=tasting_notes)


# API Queries

@app.route('/api/add_bottle',  methods=["POST"])
def api_add_bottle():
    UPLOAD_FOLDER = "./static/bottles"
    data = request.json  # Parse JSON data from the request body

    try:
        # Extract Base64 image data
        base64_image = data.get("photo")  # Expect Base64-encoded string in "image_path"
        image_filename = None

        if base64_image:
            # Generate a unique filename for the image
            image_filename = f"{data['name'].replace(' ', '_')}_{data['brand'].replace(' ', '_')}.png"
            image_filepath = os.path.join(UPLOAD_FOLDER, image_filename)

            # Decode and save the image
            with open(image_filepath, "wb") as image_file:
                base64_image_data = base64_image.split(",")[1]  # Remove "data:image/png;base64,"
                image_file.write(base64.b64decode(base64_image_data))

            print(f"Image saved to: {image_filepath}")

        abv_data = data['abv'] if data['abv'].endswith("%") else data['abv'] + "%"

        # Add bottle to the database
        new_id = add_bottle(
            brand=data['brand'],
            name=data['name'],
            abv=abv_data,
            spirit_type=data['spirit_type'],
            subtype=data.get('subtype'),
            description=data.get('description'),
            image_path=image_filename if image_filename else None  # Save the filename in DB
        )

        return jsonify({"message": "Bottle added successfully", "id": new_id}), 201

    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/remove_entry', methods=["POST"])
def api_remove_entry():
    data = request.json

    try:
        table = data["table"]
        record_id = data["id"]
        result = remove_record(table, record_id)  # Generalized function to remove a record
        if result > 0:
            return jsonify({"message": f"Record removed from {table} successfully."}), 200
        else:
            return jsonify({"error": f"No record found with ID {record_id} in {table}."}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/make_unavailable', methods=["POST"])
def api_make_unavailable():
    data = request.json
    try:
        record_id = data["id"]
        result = update_bottle(record_id, available=0)  # Generalized function to remove a record
        if result > 0:
            return jsonify({"message": f"Bottle {record_id} is now unavailable."}), 200
        else:
            return jsonify({"error": f"No record found with ID {record_id} in Bottles."}), 404
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/add_user',  methods=["POST"])
def api_add_user():
    UPLOAD_FOLDER = "./static/users"
    data = request.json  # Parse JSON data from the request body
    print(data)

    try:
        # Extract Base64 image data
        base64_image = data.get("photo")  # Expect Base64-encoded string in "image_path"
        image_filename = None

        if base64_image:
            # Generate a unique filename for the image
            image_filename = f"{data['name'].replace(' ', '_')}.png"
            image_filepath = os.path.join(UPLOAD_FOLDER, image_filename)

            # Decode and save the image
            with open(image_filepath, "wb") as image_file:
                base64_image_data = base64_image.split(",")[1]  # Remove "data:image/png;base64,"
                image_file.write(base64.b64decode(base64_image_data))

            print(f"Image saved to: {image_filepath}")

        # Add botusertle to the database
        new_id = add_user(
            name=data['name'],
            image_path=image_filename if image_filename else None  # Save the filename in DB
        )

        return jsonify({"message": "User added successfully", "id": new_id}), 201

    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

def add_notes_to_review(notes, review_id):
    """
    Adds a list of notes to a review by associating each note with a tasting note ID and review ID.
    
    Parameters:
    - notes (list): A list of selected checkbox names (e.g., note_Fruity, subnote_cooked_fruit).
    - review_id (int): The ID of the review to associate the notes with.
    
    Returns:
    - int: The number of notes added to the review, or None if an error occurs.
    """
    stripped_notes = []

    # Strip the prefixes from each note and add to the list
    for note in notes:
        # Strip the prefix from the note name (note_, subnote_, subsubnote_)
        if note.startswith("note_"):
            stripped_notes.append(note[len("note_"):])  # Remove "note_" prefix
        elif note.startswith("subnote_"):
            stripped_notes.append(note[len("subnote_"):])  # Remove "subnote_" prefix
        elif note.startswith("subsubnote_"):
            stripped_notes.append(note[len("subsubnote_"):])  # Remove "subsubnote_" prefix
        else:
            stripped_notes.append(note)

    # Now add each stripped note to the review
    for note_name in stripped_notes:
        # Retrieve the tasting note ID from the note name
        tasting_note_id = get_tasting_note_id(note_name)
        
        if tasting_note_id:
            # Add the note record to the database
            success = add_note_record(review_id, tasting_note_id)
            
            if not success:
                print(f"Failed to add the note: {note_name}")
        
    return len(stripped_notes)  # Return the number of notes added


@app.route('/api/add_review', methods=["POST"])
def api_add_review():
    """
    API endpoint to add a review for a specific bottle by a user.
    """
    data = request.json  # Parse JSON data from the request body
    print(data)
    try:
        # Extract data from the request
        name = data.get('name')
        review = data.get('review_text')
        notes = data.get('notes')
        score = int(data.get('score'))
        bottle_id = int(data.get('bottle_id'))
        if data.get('event_id'):
            event_id = int(data.get('event_id'))
        else:
            event_id = None

        # Validate required fields
        if not all([name, review, score, bottle_id]):
            return jsonify({"error": "Missing required fields"}), 400

        # Get user ID based on the name
        user_id = None

        try:
            user_id = int(name)
        except:
            user_id = get_user_id_by_name(name)

        if user_id is None:
            print(name)
            return jsonify({"error": f"User with name '{name}' not found"}), 404

        # Add the review to the database
        review_id = add_review(user_id, bottle_id, review, score, event_id=event_id)
        if notes and review_id:
            add_notes_to_review(notes, review_id)
        else:
            return jsonify({"error": "Failed to add review"}), 500

        if review_id:
            return jsonify({"message": "Review added successfully", "review_id": review_id}), 201
        else:
            return jsonify({"error": "Failed to add review"}), 500

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/random_bottle_id', methods=["GET"])
def random_bottle_id():
    """Fetch the ID of a random available bottle."""
    random_bottle = get_random_available_bottle_id()
    if isinstance(random_bottle, dict) and "error" in random_bottle:
        return random_bottle  # Return error if no bottles are available
    return jsonify({"id": random_bottle["id"]})

@app.route('/api/add_event', methods=["POST"])
def api_add_event():
    try:
        data = request.json
        event_date = data.get("event_date")
        name = data.get("name")
        folder_path = "./static/events/" + name + str(event_date)
        code = name + str(event_date)

        if not name or not event_date:
            return jsonify({"error": "Name and event date are required."}), 400

        # Add event to the database
        add_event(code, event_date, folder_path, name)

        return jsonify({"message": "Event added successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/add_bottles_to_event', methods=["POST"])
def api_add_bottles_to_event():
    event_id = request.form.get("event_id")
    bottle_ids = request.form.get("bottle_ids", "").split(",")
    print(event_id)
    if not event_id or not bottle_ids:
        return jsonify({"error": "Event ID and bottle IDs are required"}), 400

    try:
        add_bottle_to_event(bottle_ids, event_id)
        return redirect(request.referrer)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/add_users_to_event', methods=["POST"])
def api_add_users_to_event():
    event_id = request.form.get("event_id")
    user_ids = request.form.get("user_ids", "").split(",")
    if not event_id or not user_ids:
        return jsonify({"error": "Event ID and user IDs are required"}), 400

    try:
        add_user_to_event(user_ids, event_id)
        return redirect(request.referrer)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/user_exists', methods=["POST"])
def api_user_exists():
    name = str(request.form.get("name")).capitalize()
    user_id = get_user_id_by_name(name)

    if not user_id:
        return jsonify({"error": "User not found"}), 404

    # Create a response and set the cookie
    response = jsonify({"user_id": user_id})
    response.set_cookie("user_id", str(user_id), max_age=36000, httponly=True)  # Cookie expires in 1 hour
    return response

@app.route('/api/upload_event_photo_file', methods=['POST'])
def upload_photo():
    event_id = request.form.get("event_id")
    image_file = request.files.get("image_file")
    event = get_event_by_id(event_id)

    if not image_file or not event_id:
        return jsonify({"error": "Invalid data"}), 400

    try:

        # Create event-specific directory
        os.makedirs(event["folder_path"], exist_ok=True)

        # Save the file
        file_path = os.path.join(event["folder_path"], f"photo_{len(os.listdir(event['folder_path'])) + 1}.png")
        image_file.save(file_path)

        return redirect(request.referrer)
    except Exception as e:
        print(f"Error uploading photo: {e}")
        return jsonify({"error": "Failed to upload photo"}), 500

@app.route('/api/upload_event_photo_b64', methods=['POST'])
def upload_event_photo():
    event_id = request.form.get("event_id")
    event = get_event_by_id(event_id)
    image_data = request.form.get("image_data")
    if not event_id or not image_data:
        return jsonify({"error": "Event ID and image data are required"}), 400

    try:
        # Decode the image
        header, encoded = image_data.split(",", 1)
        image = base64.b64decode(encoded)

        # Create event-specific directory
        os.makedirs(event["folder_path"], exist_ok=True)

        # Save the image
        file_path = os.path.join(event["folder_path"], f"photo_{len(os.listdir(event['folder_path'])) + 1}.png")
        with open(file_path, "wb") as f:
            f.write(image)

        return jsonify({"message": "Photo uploaded successfully", "file_path": file_path}), 200
    except Exception as e:
        print(f"Error uploading photo: {e}")
        return jsonify({"error": "Failed to upload photo"}), 500
    
@app.route('/api/edit_expert_notes', methods=['POST'])
def edit_expert_notes():
    """
    Endpoint to handle form submissions for editing expert notes and updating the bottle description.
    """
    try:
        data = request.json
        bottle_id = data.get('bottle_id')
        description = data.get('description', '')
        tasting_notes = data.get('notes', [])  # List of tasting note names
        print(data)
        stripped_notes = []

        
        if not bottle_id:
            return jsonify({"error": "Bottle ID is required"}), 400

        # Strip the prefixes from each note and add to the list
        for note in tasting_notes:
            # Strip the prefix from the note name (note_, subnote_, subsubnote_)
            if note.startswith("note_"):
                stripped_notes.append(note[len("note_"):])  # Remove "note_" prefix
            elif note.startswith("subnote_"):
                stripped_notes.append(note[len("subnote_"):])  # Remove "subnote_" prefix
            elif note.startswith("subsubnote_"):
                stripped_notes.append(note[len("subsubnote_"):])  # Remove "subsubnote_" prefix
            else:
                stripped_notes.append(note)

        # Convert bottle_id to an integer
        bottle_id = int(bottle_id)

        # Map tasting note names to IDs
        tasting_note_ids = []
        for note_name in stripped_notes:
            note_id = get_tasting_note_id(note_name)
            if note_id is not None:
                tasting_note_ids.append(note_id)

        if tasting_note_ids:
            print(tasting_note_ids)
            # Update the expert notes
            update_expert_notes(bottle_id, tasting_note_ids)

        if description:
            # Update the bottle description
            update_bottle_description(bottle_id, description)

        # Return a success response
        return jsonify({"success": True, "message": "Expert notes and description updated successfully!"}), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500

#BOOLEAN DATA VALIDATION FUNCTIONS

@app.route("/api/check_bottle", methods=["GET"])
def check_bottle():
    brand = request.args.get("brand").capitalize()
    name = request.args.get("name").capitalize()

    exists = bottle_exists(brand, name)
    return jsonify({"exists": exists})

@app.route("/api/check_user", methods=["GET"])
def check_user():
    name = request.args.get("name").capitalize()

    exists = user_exists(name)
    return jsonify({"exists": exists})


if __name__ == '__main__':
    #app.run(host="0.0.0.0", port=5000, debug=True, ssl_context=("./cert.pem", "./key.pem"))
    app.run(host="0.0.0.0", port=5000, debug=True)



