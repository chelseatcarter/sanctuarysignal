from flask import Flask, render_template, jsonify, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from models import ZipCode, db, User, Alert, AlertVote
import random
import re
import json
import os
from dotenv import load_dotenv
from twilio.rest import Client
from werkzeug.utils import secure_filename
from flask import send_from_directory
import requests
import boto3
from sqlalchemy.orm import joinedload

load_dotenv()

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:s23RnnVoH5OQL5rbsxqC8FI3MckaOsqZ@dpg-d1vcvher433s73fiogn0-a.ohio-postgres.render.com/sanctuarysignal'
db.init_app(app)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
VERIFY_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")
MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

s3 = boto3.client('s3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
print(f"✅ TWILIO_ACCOUNT_SID: {TWILIO_ACCOUNT_SID}")
print(f"✅ TWILIO_AUTH_TOKEN starts with: {TWILIO_AUTH_TOKEN[:4]}... (length: {len(TWILIO_AUTH_TOKEN)})")
print(f"✅ VERIFY_SID: {VERIFY_SID}")
print(f"✅ MESSAGING_SERVICE_SID: {MESSAGING_SERVICE_SID}")

@app.route('/')
def home():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None

    user_lat = None
    user_lng = None
    # If user is logged in, get their latitude and longitude from the zip code and display it on the map
    if user and user.zip_code:
        zip_record = ZipCode.query.filter_by(zip_code=user.zip_code).first()
        if zip_record:
            user_lat = zip_record.lat
            user_lng = zip_record.lng

    return render_template('home.html', user=user, user_lat=user_lat, user_lng=user_lng, google_api_key=GOOGLE_API_KEY)

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

        try:
            twilio_client.verify.services(VERIFY_SID).verifications.create(to=user.phone_number, channel='sms')
        except Exception as e:
            app.logger.error(f"❌ Twilio error: {e}")
            return jsonify({"error": "Failed to send verification code"}), 500

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info(f"Login data: {data}")

        user = User.query.filter_by(username=data['username']).first()
        if user and user.check_password(data['password']):

            if not user.verified:
                twilio_client.verify.services(VERIFY_SID).verifications.create(to=user.phone_number, channel='sms')
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

def extract_zip_from_address(address):
    """Extract 5-digit ZIP code from a U.S. address string"""
    match = re.search(r'\b\d{5}\b', address)
    return match.group() if match else None

def generate_alert_message(alert_type, address):
    alert_type = alert_type.lower()
    templates = {
        'suspicious': f"⚠️ Suspicious activity reported near {address}. \n\n\n⚠️ Actividad sospechosa en tu área. Mantente alerta.",
        'emergency': f"🚨 Emergency reported at {address}. If you or others are in danger, call 911 immediately. ",
        'ice': f"🚓 ICE presence reported at {address}. \n\n\n🚨 Actividad de ICE reportada cerca. \n\nKnow your rights: https://nilc.org/kyr.",
        'disturbance': f"🔊 Disturbance reported at {address}. Authorities may be responding.",
        'other': f"📢 An incident has been reported at {address}. If this alert concerns you, check the community board for updates."
    }
    return templates.get(alert_type, f"🚨 Incident reported at {address}.")

# from datetime import datetime
# from models import Alert

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_zip_from_coords(lat, lng):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Missing Google API key")

    response = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params={
        'latlng': f'{lat},{lng}',
        'key': api_key
    })

    results = response.json().get("results", [])
    for result in results:
        for component in result.get("address_components", []):
            if "postal_code" in component.get("types", []):
                return component.get("short_name")
    return None

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        alert_type = request.form.get('type')
        address = request.form.get('address')
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')
        photo_file = request.files.get('photo')
        description = request.form.get('description')
        user_id = session.get('user_id')

        if not all([alert_type, address, lat, lng, user_id]):
            return jsonify({"error": "Missing required fields"}), 400

        # Reverse geocode ZIP from lat/lng
        zip_code = get_zip_from_coords(lat, lng)
        if not zip_code:
            return jsonify({"error": "Could not determine ZIP code from coordinates"}), 400

        zip_record = ZipCode.query.filter_by(zip_code=zip_code).first()
        if not zip_record:
            return jsonify({"error": "Invalid ZIP code"}), 400

        body_message = generate_alert_message(alert_type, address)
        county_name = zip_record.county_name

        photo_url = None
        if photo_file and allowed_file(photo_file.filename):
            filename = secure_filename(photo_file.filename)
            s3.upload_fileobj(photo_file, S3_BUCKET, filename)
            photo_url = f"https://{S3_BUCKET}.s3.us-east-2.amazonaws.com/{filename}"

        # Save the alert
        alert = Alert(
            alert_type=alert_type,
            address=address,
            lat=float(lat),
            lng=float(lng),
            description=description,
            user_id=user_id,
            photo=photo_url,
            zip_code=zip_code
        )
        db.session.add(alert)
        db.session.commit()

        # Twilio messaging setup
        from twilio.rest import Client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        messaging_service_sid = os.getenv("TWILIO_VERIFY_SERVICE_SID")

        client = Client(account_sid, auth_token)
        

        # Find all verified & not banned users in the same county
        users = User.query.filter_by(county_name=county_name, verified=True, banned=False).all()
        for u in users:
            if is_valid_e164(u.phone_number):
                try:
                    message = twilio_client.messages.create(
                        messaging_service_sid=MESSAGING_SERVICE_SID,
                        body=body_message,
                        to=u.phone_number
                    )
                    print(f"Sent to {u.phone_number} | SID: {message.sid}")
                except Exception as e:
                    print(f"Failed to send to {u.phone_number}: {e}")

        return redirect('/')

    return render_template('report.html')

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
    return {'message': 'Database initialized successfully'}

@app.route('/api/events')
def get_alerts_for_map():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])

    user = User.query.get(user_id)
    if not user or not user.county_name:
        return jsonify([])

    alerts = (
        db.session.query(Alert)
        .join(ZipCode, Alert.zip_code == ZipCode.zip_code)
        .filter(ZipCode.county_name == user.county_name)
        .order_by(Alert.timestamp.desc())
        .all()
    )

    events = []
    for alert in alerts:
        events.append({
            'id': alert.id,
            'lat': alert.lat,
            'lng': alert.lng,
            'title': alert.alert_type,
            'timestamp': alert.timestamp.isoformat(),
            'description': alert.description,
            'address': alert.address,
            'zip_code': alert.zip_code,
            'county_name': user.county_name,
            'false_votes': alert.false_votes
        })

    return jsonify(events)

@app.route('/api/alerts/list')
def display_list_events():
    alerts = Alert.query.order_by(Alert.timestamp.desc()).all()
    events = []

    for alert in alerts:
        events.append({
            'id': alert.id,
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


