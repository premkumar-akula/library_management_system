from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import secrets
import re
from dotenv import load_dotenv
from pathlib import Path
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timezone
from pymongo import MongoClient
from bson.objectid import ObjectId
import json



# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
load_dotenv()

# Configuration
app.secret_key = os.getenv('SECRET_KEY')
app.config['MONGO_URI'] = os.getenv('MONGO_URI')

# Initialize extensions
mongo = PyMongo(app)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client['library_db']
books_col = db.books
borrowed_books_col = db.borrowed_books
books_collection = db['books']
borrowed_books_col = db['borrowed_books']


# MongoDB Configuration
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/library_management')
client = MongoClient(MONGODB_URI)
db = client.get_database()

# No need for a separate class, we'll use MongoDB collections directly
# But you can create a helper function for structure:

def create_support_ticket(user_id, message):
    """Helper function to create a ticket structure"""
    return {
        'user_id': ObjectId(user_id),  # Convert to ObjectId if storing references
        'message': message,
        'response': None,
        'created_at': datetime.utcnow(),
        'status': 'open',
        'user_info': {  # You can denormalize some user data for easier queries
            'name': None,  # Will be populated when creating ticket
            'email': None
        }
    }
# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = mongo.db.users.find_one({'email': email})
        
        if user:
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=1)
            
            mongo.db.password_resets.insert_one({
                'email': email,
                'token': token,
                'expires_at': expiry
            })
            
            # In production, implement actual email sending
            reset_link = url_for('reset_password', token=token, _external=True)
            print(f"Password reset link for {email}: {reset_link}")
        
        flash('If an account exists with this email, you will receive a password reset link.', 'info')
        return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_request = mongo.db.password_resets.find_one({
        'token': token,
        'expires_at': {'$gt': datetime.now()}
    })
    
    if not reset_request:
        flash('Invalid or expired token', 'danger')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(request.url)
        
        mongo.db.users.update_one(
            {'email': reset_request['email']},
            {'$set': {'password': generate_password_hash(password)}}
        )
        
        mongo.db.password_resets.delete_one({'token': token})
        
        flash('Password updated successfully! Please login.', 'success')
        return redirect(url_for('user_login'))
    
    return render_template('reset_password.html', token=token)

# Remove the combined login route and keep these separate routes:

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('user_login'))
        
        user = mongo.db.users.find_one({'email': email, 'role': 'user'})
        
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
        
        admin = mongo.db.users.find_one({'email': email, 'role': 'admin'})
        
        if admin and check_password_hash(admin['password'], password):
            session['user_id'] = str(admin['_id'])
            session['role'] = 'admin'
            session['name'] = admin.get('full_name', 'Admin')
            return redirect(url_for('admin_dashboard'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('admin_login.html')

# User Signup Route
# Keep only one definition like this:

@app.route('/user/signup', methods=['GET', 'POST'])
def user_signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')  # New field
        
        # Validate passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('user_signup'))
            
        # Rest of your validation
        if not all([full_name, email, mobile, password, confirm_password]):
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('user_signup'))
        
        existing_user = mongo.db.users.find_one({'$or': [{'email': email}, {'mobile': mobile}]})
        if existing_user:
            flash('Email or mobile already registered', 'danger')
            return redirect(url_for('user_signup'))
        
        # Create new user
        mongo.db.users.insert_one({
            'full_name': full_name,
            'email': email,
            'mobile': mobile,
            'password': generate_password_hash(password),
            'role': 'user',
            'created_at': datetime.now()
        })
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('user_login'))
    
    return render_template('user_signup.html')

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')  # New field
        admin_key = request.form.get('admin_key')
        
        # Validate passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('admin_signup'))
            
        # Rest of your validation
        if not all([full_name, email, mobile, password, confirm_password, admin_key]):
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('admin_signup'))
                 # Check if admin already exists
        existing_admin = mongo.db.users.find_one({'$or': [{'email': email}, {'mobile': mobile}]})
        if existing_admin:
            flash('Email or mobile already registered', 'danger')
            return redirect(url_for('admin_signup'))
        
        # Create new admin
        mongo.db.users.insert_one({
            'full_name': full_name,
            'email': email,
            'mobile': mobile,
            'password': generate_password_hash(password),
            'role': 'admin',
            'created_at': datetime.now()
        })
        
        flash('Admin registration successful! Please login.', 'success')
        return redirect(url_for('admin_login'))
    
    return render_template('admin_signup.html')

@app.route('/user/dashboard')
def user_dashboard():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('login'))
    return render_template('user_dashboard.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login', type='admin'))
    return render_template('admin_dashboard.html')


@app.route('/admin/books')
def admin_books():
    query = request.args.get('q', '')
    selected_category = request.args.get('category', '')

    # Fetch unique categories
    categories = books_collection.distinct('type')

    # Build filter based on query and category
    filter_query = {}
    if query:
        filter_query['$or'] = [
            {'title': {'$regex': query, '$options': 'i'}},
            {'author': {'$regex': query, '$options': 'i'}}
        ]
    if selected_category:
        filter_query['type'] = selected_category

    books = list(books_collection.find(filter_query))
    return render_template('books.html', books=books, categories=categories)

@app.route('/admin/add-book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        new_book = {
            'title': request.form['title'],
            'author': request.form['author'],
            'type': request.form['type'],
            'price': float(request.form['price']),
            'image': request.form['image']
        }
        books_collection.insert_one(new_book)
        return redirect(url_for('admin_books'))
    return render_template('add_book.html')

@app.route('/admin/edit-book/<book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    from bson.objectid import ObjectId
    book = books_collection.find_one({'_id': ObjectId(book_id)})
    if request.method == 'POST':
        updated_book = {
            'title': request.form['title'],
            'author': request.form['author'],
            'type': request.form['type'],
            'price': float(request.form['price']),
            'image': request.form['image']
        }
        books_collection.update_one({'_id': ObjectId(book_id)}, {'$set': updated_book})
        return redirect(url_for('admin_books'))
    return render_template('edit_book.html', book=book)

@app.route('/admin/delete-book/<book_id>')
def delete_book(book_id):
    from bson.objectid import ObjectId
    books_collection.delete_one({'_id': ObjectId(book_id)})
    return redirect(url_for('admin_books'))

@app.route('/admin/borrowed-books')
def borrowed_books():
    borrowed_books = list(borrowed_books_col.find())
    return render_template('borrowed_books.html', borrowed_books=borrowed_books)


@app.route("/admin/add-borrowed-book", methods=["GET", "POST"])
def add_borrowed_book():
    if request.method == "POST":
        student_name = request.form['student_name']
        student_id = request.form['student_id']
        year = request.form['year']
        book_title = request.form['book_title']
        borrow_date = request.form['borrow_date']
        status = request.form['status']

        borrowed_books_col.insert_one({
            "student_name": student_name,
            "student_id": student_id,
            "year": year,
            "book_title": book_title,
            "borrow_date": borrow_date,
            "status": status 
        })

        return redirect("/admin/borrowed-books")

    return render_template("add_borrowed_book.html")


@app.route("/admin/edit-borrowed-book/<id>", methods=["GET", "POST"])
def edit_borrowed_book(id):
    entry = borrowed_books_col.find_one({"_id": ObjectId(id)})

    if request.method == "POST":
        updated_entry = {
            "student_name": request.form['student_name'],
            "student_id": request.form['student_id'],
            "year": request.form['year'],
            "book_title": request.form['book_title'],
            "borrow_date": request.form['borrow_date'],
            "status": request.form['status']
        }

        borrowed_books_col.update_one({"_id": ObjectId(id)}, {"$set": updated_entry})
        return redirect("/admin/borrowed-books")

    return render_template("edit_borrowed_book.html", entry=entry)


@app.route("/admin/delete-borrowed-book/<id>")
def delete_borrowed_book(id):
    borrowed_books_col.delete_one({"_id": ObjectId(id)})
    return redirect("/admin/borrowed-books")

@app.route('/admin/categories')
def categories():
    pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    category_data = list(books_col.aggregate(pipeline))
    return render_template('categories.html', categories=category_data)

#USER PAGE ROUTES

@app.route('/user/books')
def user_books():
    query = request.args.get('q', '')
    category = request.args.get('category', '')

    filter_query = {}
    if query:
        filter_query['title'] = {'$regex': query, '$options': 'i'}
    if category:
        filter_query['type'] = category

    books = list(db.books.find(filter_query))
    categories = db.books.distinct("type")

    return render_template('user_books.html', books=books, categories=categories, query=query)

# Support routes
@app.route('/support')
def user_support():
    if 'user_id' not in session:
        flash('Please login to access support', 'warning')
        return redirect(url_for('login'))
    
    # Get user's tickets if needed
    tickets = []
    if 'user_id' in session:
        tickets = list(mongo.db.tickets.find({
            'user_id': ObjectId(session['user_id'])
        }).sort('created_at', -1))
    
    return render_template('user_support.html', tickets=tickets)

@app.route('/submit-ticket', methods=['POST'])
def submit_ticket():
    if 'user_id' not in session:
        flash('Please login to submit a ticket', 'warning')
        return redirect(url_for('login'))
    
    issue_type = request.form.get('issue_type')
    description = request.form.get('description')
    
    if not issue_type or not description:
        flash('Please fill all required fields', 'danger')
        return redirect(url_for('user_support'))
    
    # Create ticket with timezone-aware datetime
    ticket_data = {
        'user_id': ObjectId(session['user_id']),
        'issue_type': issue_type,
        'description': description,
        'status': 'open',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'resolution': None,
        'resolved_at': None
    }
    
    try:
        mongo.db.tickets.insert_one(ticket_data)
        flash('Your support ticket has been submitted successfully!', 'success')
        return redirect(url_for('user_support'))
    except Exception as e:
        app.logger.error(f"Ticket submission error: {str(e)}")
        flash('An error occurred while submitting your ticket', 'danger')
        return redirect(url_for('user_support'))

# Admin Support Routes
@app.route('/admin/support')
def admin_support():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('admin_login'))
    
    # Get all tickets with user information
    tickets = list(mongo.db.tickets.aggregate([
        {
            '$lookup': {
                'from': 'users',
                'localField': 'user_id',
                'foreignField': '_id',
                'as': 'user'
            }
        },
        {'$unwind': '$user'},
        {'$sort': {'created_at': -1}}
    ]))
    
    return render_template('admin_support.html', tickets=tickets)

@app.route('/admin/support/resolve/<ticket_id>', methods=['POST'])
def resolve_ticket(ticket_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('admin_login'))
    
    resolution = request.form.get('resolution')
    
    if not resolution:
        flash('Resolution text is required', 'danger')
        return redirect(url_for('admin_support'))
    
    mongo.db.tickets.update_one(
        {'_id': ObjectId(ticket_id)},
        {'$set': {
            'status': 'resolved',
            'resolution': resolution,
            'resolved_at': datetime.utcnow()
        }}
    )
    
    flash('Ticket resolved successfully', 'success')
    return redirect(url_for('admin_support'))

# Collections
books_collection = db.books
users_collection = db.users
admin_collection = db.admin
borrowed_books_collection = db.borrowed_books
tickets_collection = db.tickets

@app.route('/')
def home():
    return redirect(url_for('user_books'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

    
# Add this for Vercel deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    app.run(debug=True)