from flask import Flask, render_template, jsonify, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from models import ZipCode, db, User, Alert, AlertVote
import random
import re
import json
import os
from dotenv import load_dotenv
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:s23RnnVoH5OQL5rbsxqC8FI3MckaOsqZ@dpg-d1vcvher433s73fiogn0-a.ohio-postgres.render.com/sanctuarysignal'
db.init_app(app)

@app.route('/')
def home():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    return render_template('home.html', user=user)


TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
VERIFY_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


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

        if User.query.filter_by(phone_number=data['phone_number']).first():
            return jsonify({"error": "Phone number already exists"}), 400
        
        # Lookup county_name from zip_codes table
        zip_record = ZipCode.query.filter_by(zip_code=data['zip_code']).first()
        if not zip_record:
            return jsonify({"error": "Invalid ZIP code"}), 400

        # Now stores county_name from zip_codes table
        user = User(
            username=data['username'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone_number=data['phone_number'],
            zip_code=data['zip_code'],
            county_name=zip_record.county_name
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        verification = twilio_client.verify.services(VERIFY_SID).verifications.create(to=user.phone_number, channel='sms')

        return jsonify({"message": "Signup successful"}), 201

    return render_template('signup.html')

@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json()
    phone = data['phone_number']
    code = data['code']

    check = twilio_client.verify.services(VERIFY_SID).verification_checks.create(to=phone, code=code)
    if check.status != "approved":
        return jsonify({"error": "Invalid verification code"}), 400
    
    # Find user by phone number and set them to verified
    user = User.query.filter_by(phone_number=phone).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if check.status == "approved":
        user.verified = True
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id  # Set session for the user

    return jsonify({"message": "Phone number verified and user logged in!"}), 200

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

            if not user.verified:
                verification = twilio_client.verify.services(VERIFY_SID).verifications.create(to=user.phone_number, channel='sms')
                return jsonify({
                    "error": "Account not verified",
                    "phone_number": user.phone_number  # now the frontend can grab it
                }), 403

            if user.banned:
                return jsonify({"error": "Your account has been banned."}), 403

            session['user_id'] = user.id  # Set session
            return jsonify({
                "message": "Login successful",
                "user_id": user.id,
                "verified": user.verified,
                "banned": user.banned
            }), 200

        return jsonify({"error": "Invalid credentials"}), 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info(f"Report data: {data}")
        return jsonify({"message": "Report received"})

    return render_template('report.html')

@app.route('/send_sms', methods=['POST'])
def send_sms():
    data = request.get_json()
    from_number = data.get("from_number")  # Supplied Twilio number
    county_name = data.get("county_name")  # County name for the alert
    message_body = data.get("message")

    if not all([from_number, county_name, message_body]):
        return jsonify({"error": "Missing from_number, county_name, or message"}), 400

    if not is_valid_e164(from_number):
        return jsonify({"error": "Invalid phone number format (must be E.164)"}), 400
    
    # Get phone numbers of users in the county
    users = User.query.filter_by(county_name=county_name, verified=True, banned=False).all()
    phone_numbers = [u.phone_number for u in users if is_valid_e164(u.phone_number)]

    if not phone_numbers:
        return jsonify({"error": "No valid phone numbers found for this county"}), 404

    # Send SMS to all phone numbers
    results = []
    for to_number in phone_numbers:
        try:
            message = twilio_client.messages.create(
                body=message_body,
                from_=from_number,
                to=to_number
            )
            results.append({"to": to_number, "status": "sent", "sid": message.sid})
        except Exception as e:
            results.append({"to": to_number, "status": "failed", "error": str(e)})

    return jsonify({"results": results}), 200

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
    return {'message': 'Database initialized successfully'}

@app.route('/api/alerts/map')
def get_alerts_for_map():
    alerts = Alert.query.all()
    events = []

    for alert in alerts:
        events.append({
            'lat': alert.lat,
            'lng': alert.lng,
            'title': alert.alert_type
        })

    return jsonify(events)

@app.route('/api/alerts/list')
def display_list_events():
    alerts = Alert.query.all()
    events = []

    for alert in alerts:
        events.append({
            'username': alert.user.username,
            'timestamp': alert.timestamp.isoformat(),
            'address': alert.address,
            'description': alert.description,
            'alert_type': alert.alert_type
        })

    return jsonify(events)

@app.route('/api/alerts/details/<int:alert_id>')
def display_alert_details(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    event = {
        'username': alert.user.username,
        'timestamp': alert.timestamp.isoformat(),
        'address': alert.address,
        'description': alert.description,
        'alert_type': alert.alert_type,
        'photo': alert.photo
    }
    return jsonify(event)

@app.route('/alerts/<int:alert_id>')
def alert_detail_page(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    return render_template('alert_detail.html', alert=alert)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


