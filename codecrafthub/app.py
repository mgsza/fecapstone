from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Name of the JSON file used to store course data
DATA_FILE = "courses.json"

# Allowed status values for a course
VALID_STATUSES = ["Not Started", "In Progress", "Completed"]


# -----------------------------
# Helper functions
# -----------------------------

def ensure_data_file():
    """
    Create the JSON data file automatically if it does not exist.
    The file will start with an empty list because we are storing courses as a list.
    """
    if not os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "w") as file:
                json.dump([], file, indent=4)
        except OSError as e:
            raise IOError(f"Could not create data file: {str(e)}")


def load_courses():
    """
    Read all courses from the JSON file.
    Returns a Python list of course dictionaries.
    """
    ensure_data_file()

    try:
        with open(DATA_FILE, "r") as file:
            data = json.load(file)

            # Make sure the file contains a list
            if not isinstance(data, list):
                raise ValueError("Invalid data format in courses.json. Expected a list.")

            return data
    except json.JSONDecodeError:
        raise ValueError("Could not parse courses.json. File contains invalid JSON.")
    except OSError as e:
        raise IOError(f"Could not read data file: {str(e)}")


def save_courses(courses):
    """
    Write the full list of courses back to the JSON file.
    """
    try:
        with open(DATA_FILE, "w") as file:
            json.dump(courses, file, indent=4)
    except OSError as e:
        raise IOError(f"Could not write to data file: {str(e)}")


def get_next_id(courses):
    """
    Generate the next course ID.
    IDs start from 1 and increase by 1.
    """
    if not courses:
        return 1
    return max(course["id"] for course in courses) + 1


def find_course_by_id(courses, course_id):
    """
    Find a course in the list by its ID.
    Returns the course if found, otherwise None.
    """
    for course in courses:
        if course["id"] == course_id:
            return course
    return None


def is_valid_date(date_string):
    """
    Validate that the date is in YYYY-MM-DD format.
    Returns True if valid, otherwise False.
    """
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_course_data(data, is_update=False):
    """
    Validate incoming course data.

    Parameters:
    - data: JSON request body
    - is_update: True for PUT requests, False for POST requests

    Returns:
    - None if validation passes
    - error message string if validation fails
    """

    # Make sure request body exists and is valid JSON
    if not data:
        return "Request body must be valid JSON."

    required_fields = ["name", "description", "target_date", "status"]

    # For creating a new course, all fields are required
    if not is_update:
        for field in required_fields:
            if field not in data or str(data[field]).strip() == "":
                return f"Missing required field: {field}"

    # For updating, only validate fields if they are included
    if "name" in data and str(data["name"]).strip() == "":
        return "Field 'name' cannot be empty."

    if "description" in data and str(data["description"]).strip() == "":
        return "Field 'description' cannot be empty."

    if "target_date" in data:
        if str(data["target_date"]).strip() == "":
            return "Field 'target_date' cannot be empty."
        if not is_valid_date(data["target_date"]):
            return "Field 'target_date' must be in YYYY-MM-DD format."

    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return f"Invalid status value. Must be one of: {', '.join(VALID_STATUSES)}"

    return None


# -----------------------------
# Routes
# -----------------------------

@app.route("/api/courses", methods=["POST"])
def add_course():
    """
    Create a new course.
    """
    try:
        data = request.get_json()

        # Validate the incoming request data
        error = validate_course_data(data, is_update=False)
        if error:
            return jsonify({"error": error}), 400

        courses = load_courses()

        # Build the new course object
        new_course = {
            "id": get_next_id(courses),
            "name": data["name"].strip(),
            "description": data["description"].strip(),
            "target_date": data["target_date"],
            "status": data["status"],
            "created_at": datetime.now().isoformat()
        }

        # Add the course to the list and save it
        courses.append(new_course)
        save_courses(courses)

        return jsonify({
            "message": "Course created successfully.",
            "course": new_course
        }), 201

    except (IOError, ValueError) as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500


@app.route("/api/courses", methods=["GET"])
def get_all_courses():
    """
    Return all courses.
    """
    try:
        courses = load_courses()
        return jsonify(courses), 200

    except (IOError, ValueError) as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    """
    Return one specific course by ID.
    """
    try:
        courses = load_courses()
        course = find_course_by_id(courses, course_id)

        if not course:
            return jsonify({"error": "Course not found."}), 404

        return jsonify(course), 200

    except (IOError, ValueError) as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    """
    Update an existing course by ID.
    """
    try:
        data = request.get_json()

        # Validate the incoming request data for update
        error = validate_course_data(data, is_update=True)
        if error:
            return jsonify({"error": error}), 400

        courses = load_courses()
        course = find_course_by_id(courses, course_id)

        if not course:
            return jsonify({"error": "Course not found."}), 404

        # Update only the fields provided in the request
        if "name" in data:
            course["name"] = data["name"].strip()

        if "description" in data:
            course["description"] = data["description"].strip()

        if "target_date" in data:
            course["target_date"] = data["target_date"]

        if "status" in data:
            course["status"] = data["status"]

        save_courses(courses)

        return jsonify({
            "message": "Course updated successfully.",
            "course": course
        }), 200

    except (IOError, ValueError) as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    """
    Delete a course by ID.
    """
    try:
        courses = load_courses()
        course = find_course_by_id(courses, course_id)

        if not course:
            return jsonify({"error": "Course not found."}), 404

        courses.remove(course)
        save_courses(courses)

        return jsonify({
            "message": f"Course with id {course_id} deleted successfully."
        }), 200

    except (IOError, ValueError) as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500


# Optional home route for quick testing
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome to CodeCraftHub API"}), 200


# -----------------------------
# App entry point
# -----------------------------
if __name__ == "__main__":
    # Make sure the JSON file exists before starting the app
    try:
        ensure_data_file()
    except Exception as e:
        print(f"Error initializing data file: {e}")

    # Run the Flask development server
    app.run(debug=True)