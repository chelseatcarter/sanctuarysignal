from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from models import db, User
import random
import re
import json

app = Flask(__name__)

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:s23RnnVoH5OQL5rbsxqC8FI3MckaOsqZ@dpg-d1vcvher433s73fiogn0-a.ohio-postgres.render.com/sanctuarysignal'
db.init_app(app)

@app.route('/')
def home():
    return render_template('home.html')

def is_valid_e164(number):
    return re.match(r'^\+[1-9]\d{1,14}$', number) is not None

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info(f"Signup data: {data}")
        if not is_valid_e164(data['phone_number']):
            return jsonify({"error": "Phone number must be in expected E.164 format, try again"}), 400

        if User.query.filter_by(username=data['username']).first():
            return jsonify({"error": "Username already exists"}), 400

        user = User(
            username=data['username'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_number=data['phone_number'],
            zip_code=data['zip_code'],
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        return jsonify({"message": "Signup successful"}), 201

    return render_template('signup.html')

@app.route('/debug/users')
def list_users():
    users = User.query.all()
    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "phone": user.phone_number
        } for user in users
    ])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info(f"Login data: {data}")

        user = User.query.filter_by(username=data['username']).first()
        if user and user.check_password(data['password']):
            return jsonify({
                "message": "Login successful",
                "user_id": user.id,
                "verified": user.verified,
                "banned": user.banned
            }), 200

        return jsonify({"error": "Invalid credentials"}), 401

    return render_template('login.html')


@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info(f"Report data: {data}")
        return jsonify({"message": "Report received"})

    return render_template('report.html')

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
    return {'message': 'Database initialized successfully'}

@app.route('/api/events')
def fake_events():
    # Generate 10 random points near Detroit
    base_lat, base_lng = 42.3314, -83.0458
    events = []

    for i in range(10):
        lat_offset = random.uniform(-0.03, 0.03)
        lng_offset = random.uniform(-0.03, 0.03)
        events.append({
            'lat': base_lat + lat_offset,
            'lng': base_lng + lng_offset,
            'title': f"Fake Incident #{i + 1}"
        })

    return jsonify(events)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


