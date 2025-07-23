from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from models import db, User

app = Flask(__name__)

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:s23RnnVoH5OQL5rbsxqC8FI3MckaOsqZ@dpg-d1vcvher433s73fiogn0-a.ohio-postgres.render.com/sanctuarysignal'
db.init_app(app)

@app.route('/')
def home():
    return {'message': 'Sanctuary Signal API is running'}

@app.route('/signup', methods=['GET'])
def signup():
    return render_template('signup.html')

@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
    return {'message': 'Database initialized successfully'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


