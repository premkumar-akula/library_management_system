from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')

# Use local MongoDB for development, Atlas for production
if os.environ.get('VERCEL') or os.environ.get('PRODUCTION'):
    # Production (Vercel) - Use MongoDB Atlas
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/library_management')
else:
    # Development - Use local MongoDB
    MONGODB_URI = 'mongodb://localhost:27017/library_management'

client = MongoClient(MONGODB_URI)
db = client.library_management
# MongoDB Configuration
try:
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/library_management')
    client = MongoClient(MONGODB_URI)
    db = client.library_management
    print("✅ MongoDB connected successfully")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")

# Collections
books_collection = db.books
users_collection = db.users
borrowed_books_collection = db.borrowed_books
tickets_collection = db.tickets
password_resets_collection = db.password_resets

# Initialize sample data
def init_db():
    try:
        if users_collection.count_documents({}) == 0:
            users_collection.insert_one({
                'full_name': 'Admin User',
                'email': 'admin@library.com',
                'mobile': '1234567890',
                'password': generate_password_hash('admin123'),
                'role': 'admin',
                'created_at': datetime.utcnow()
            })
            print("✅ Sample admin user created")
    except Exception as e:
        print(f"❌ Database init error: {e}")

# Initialize database
init_db()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = users_collection.find_one({'email': email})
        
        if user:
            flash('If an account exists, you will receive a reset link.', 'info')
        else:
            flash('Email not found', 'danger')
        
        return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('user_login'))
        
        user = users_collection.find_one({'email': email, 'role': 'user'})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = 'user'
            session['name'] = user.get('full_name', 'User')
            return redirect(url_for('user_dashboard'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('user_login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('admin_login'))
        
        admin = users_collection.find_one({'email': email, 'role': 'admin'})
        
        if admin and check_password_hash(admin['password'], password):
            session['user_id'] = str(admin['_id'])
            session['role'] = 'admin'
            session['name'] = admin.get('full_name', 'Admin')
            return redirect(url_for('admin_dashboard'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('admin_login.html')

@app.route('/user/signup', methods=['GET', 'POST'])
def user_signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('user_signup'))
            
        if not all([full_name, email, mobile, password, confirm_password]):
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('user_signup'))
        
        existing_user = users_collection.find_one({'$or': [{'email': email}, {'mobile': mobile}]})
        if existing_user:
            flash('Email or mobile already registered', 'danger')
            return redirect(url_for('user_signup'))
        
        users_collection.insert_one({
            'full_name': full_name,
            'email': email,
            'mobile': mobile,
            'password': generate_password_hash(password),
            'role': 'user',
            'created_at': datetime.utcnow()
        })
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('user_login'))
    
    return render_template('user_signup.html')

@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('user_login'))
    return render_template('user_dashboard.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/user/books')
def user_books():
    query = request.args.get('q', '')
    category = request.args.get('category', '')

    filter_query = {}
    if query:
        filter_query['title'] = {'$regex': query, '$options': 'i'}
    if category:
        filter_query['type'] = category

    books = list(books_collection.find(filter_query))
    categories = books_collection.distinct("type")

    return render_template('user_books.html', books=books, categories=categories, query=query)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('index'))

# Vercel requires this at the bottom
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

