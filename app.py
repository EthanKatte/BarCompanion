from flask import Flask, render_template, request, jsonify
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
                                get_random_available_bottle_id
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
        print(bottles)
        return render_template('inventory.html', bottles=bottles)

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
    return render_template('inventory.html', bottles=bottles)

@app.route('/users', methods=["GET"])
def users():
    users = get_all_users_with_reviews()
    return render_template('users.html', users=users)

@app.route('/fuckoff', methods=["GET"])
def admin_page():
    try:
        # Fetch all table contents dynamically
        tables_data = get_all_tables_contents()
        return render_template("admin.html", tables_data=tables_data)
    except Exception as e:
        return f"An error occurred: {str(e)}", 500



# API Queries

@app.route('/api/add_bottle',  methods=["POST"])
def api_add_bottle():
    UPLOAD_FOLDER = "./static/bottles"
    data = request.json  # Parse JSON data from the request body
    print(data)

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

        # Add bottle to the database
        new_id = add_bottle(
            brand=data['brand'],
            name=data['name'],
            abv=data['abv'],
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

        # Add bottle to the database
        new_id = add_user(
            name=data['name'],
            image_path=image_filename if image_filename else None  # Save the filename in DB
        )

        return jsonify({"message": "User added successfully", "id": new_id}), 201

    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/api/add_review', methods=["POST"])
def api_add_review():
    """
    API endpoint to add a review for a specific bottle by a user.
    """
    data = request.json  # Parse JSON data from the request body
    try:
        # Extract data from the request
        name = data.get('name')
        notes = data.get('notes')
        score = int(data.get('score'))
        bottle_id = int(data.get('bottle_id'))

        # Validate required fields
        if not all([name, notes, score, bottle_id]):
            return jsonify({"error": "Missing required fields"}), 400

        # Get user ID based on the name
        user_id = get_user_id_by_name(name)
        if user_id is None:
            return jsonify({"error": f"User with name '{name}' not found"}), 404

        # Add the review to the database
        review_id = add_review(user_id, bottle_id, notes, score)
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


if __name__ == '__main__':
    app.run(debug=True)
