from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db

app = Flask(__name__)

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://admin:s23RnnVoH5OQL5rbsxqC8FI3MckaOsqZ@dpg-d1vcvher433s73fiogn0-a.ohio-postgres.render.com/sanctuarysignal'
db = SQLAlchemy(app)

@app.route('/')
def home():
    return {'message': 'Sanctuary Signal API is running'}

@app.route('/init-db')
def init_db():
    db.create_all()
    return {'message': 'Database initialized successfully'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


