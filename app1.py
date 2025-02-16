from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import json
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///college.db'  # SQLite database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # Change this to a secure key

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student, faculty, contributor

# Assignment Model
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(255), nullable=False)
    submitted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Feedback Model
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feedback_text = db.Column(db.Text, nullable=False)

# Create tables
with app.app_context():
    db.create_all()

# User Registration
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

# User Login
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid email or password"}), 401

    identity = json.dumps({"id": user.id, "role": user.role})
    access_token = create_access_token(identity=identity)

    return jsonify({"access_token": access_token}), 200

# Protected Endpoint to Test JWT Authentication
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = json.loads(get_jwt_identity())
    return jsonify({
        "message": f"Welcome {current_user['id']} with role {current_user['role']}!"
    }), 200

# Submit Assignment (Student/Contributor)
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

# Add Feedback (Faculty Only)
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

# Get Feedback for an Assignment (Accessible to Faculty or the Student who submitted the assignment)
@app.route('/assignments/<int:assignment_id>/feedback', methods=['GET'])
@jwt_required()
def get_feedback(assignment_id):
    current_user = json.loads(get_jwt_identity())
    assignment = Assignment.query.get(assignment_id)

    if not assignment:
        return jsonify({"message": "Assignment not found"}), 404

    if current_user["role"] != "faculty" and assignment.submitted_by != current_user["id"]:
        return jsonify({"message": "Not authorized to view feedback for this assignment"}), 403

    feedbacks = Feedback.query.filter_by(assignment_id=assignment_id).all()
    feedback_data = [{"id": f.id, "faculty_id": f.faculty_id, "feedback_text": f.feedback_text} for f in feedbacks]

    return jsonify(feedback_data), 200

# Main function
if __name__ == "__main__":
    app.run(debug=True)
