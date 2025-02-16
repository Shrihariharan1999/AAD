from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import json

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///college.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# -----------------------------
# Database Models
# -----------------------------

# User Model: Represents a user with role (student, faculty, contributor)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# Assignment Model: Represents an assignment submission
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(255), nullable=False)
    submitted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Feedback Model: Represents faculty feedback on assignments
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feedback_text = db.Column(db.Text, nullable=False)

# Create the database tables
with app.app_context():
    db.create_all()

# -----------------------------
# Routes / Endpoints
# -----------------------------

# Home Route - Serves the index.html page
@app.route('/')
def home():
    return render_template('index.html')

# User Registration Endpoint
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, email=email, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

# User Login Endpoint
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid email or password"}), 401

    # Encode the user identity as a JSON string
    identity = json.dumps({"id": user.id, "role": user.role})
    access_token = create_access_token(identity=identity)
    return jsonify({"access_token": access_token}), 200

# Protected Endpoint to Verify JWT Authentication
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = json.loads(get_jwt_identity())
    return jsonify({
        "message": f"Welcome {current_user['id']} with role {current_user['role']}!"
    }), 200

# Submit Assignment Endpoint (accessible to students or contributors)
@app.route('/assignments', methods=['POST'])
@jwt_required()
def submit_assignment():
    current_user = json.loads(get_jwt_identity())
    if current_user["role"] not in ["student", "contributor"]:
        return jsonify({"message": "Only students and contributors can submit assignments"}), 403

    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    file_url = data.get('file_url')

    new_assignment = Assignment(title=title, description=description, file_url=file_url, submitted_by=current_user["id"])
    db.session.add(new_assignment)
    db.session.commit()

    return jsonify({"message": "Assignment submitted successfully"}), 201

# Add Feedback Endpoint (accessible to faculty only)
@app.route('/assignments/<int:assignment_id>/feedback', methods=['POST'])
@jwt_required()
def add_feedback(assignment_id):
    current_user = json.loads(get_jwt_identity())
    if current_user["role"] != "faculty":
        return jsonify({"message": "Only faculty can provide feedback"}), 403

    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"message": "Assignment not found"}), 404

    data = request.get_json()
    feedback_text = data.get('feedback_text')

    new_feedback = Feedback(assignment_id=assignment_id, faculty_id=current_user["id"], feedback_text=feedback_text)
    db.session.add(new_feedback)
    db.session.commit()

    return jsonify({"message": "Feedback added successfully"}), 201

# Get Feedback Endpoint (accessible to faculty or the student who submitted the assignment)
@app.route('/assignments/<int:assignment_id>/feedback', methods=['GET'])
@jwt_required()
def get_feedback(assignment_id):
    current_user = json.loads(get_jwt_identity())
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"message": "Assignment not found"}), 404

    # Allow access if the current user is faculty or if they submitted the assignment
    if current_user["role"] != "faculty" and assignment.submitted_by != current_user["id"]:
        return jsonify({"message": "Not authorized to view feedback for this assignment"}), 403

    feedbacks = Feedback.query.filter_by(assignment_id=assignment_id).all()
    feedback_data = [{"id": f.id, "faculty_id": f.faculty_id, "feedback_text": f.feedback_text} for f in feedbacks]
    return jsonify(feedback_data), 200

# -----------------------------
# Main function: Run the App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
