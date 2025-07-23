from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from models import db, User
import random

app = Flask(__name__)

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:s23RnnVoH5OQL5rbsxqC8FI3MckaOsqZ@dpg-d1vcvher433s73fiogn0-a.ohio-postgres.render.com/sanctuarysignal'
db.init_app(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info(f"Signup data: {data}")
        return jsonify({"message": "Signup received"})

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info(f"Login data: {data}")
        return jsonify({"message": "Login received"})

    return render_template('login.html')

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


