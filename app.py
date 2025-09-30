from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta, timezone
import secrets
import re
from dotenv import load_dotenv
from pathlib import Path
from pymongo import MongoClient
from bson.objectid import ObjectId

# Initialize Flask app
app = Flask(__name__)
load_dotenv()

# Configuration
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')

# MongoDB setup (Atlas connection)
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["library_db"]
    
    # Test connection
    client.admin.command('ping')
    print("✅ Successfully connected to MongoDB Atlas!")
    
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    # You might want to exit or handle this differently in production
    raise e

# Collections
books_col = db["books"]
borrowed_books_col = db["borrowed_books"]
users_col = db["users"]
tickets_col = db["tickets"]
password_resets_col = db["password_resets"]

# Ensure indexes for better performance
try:
    users_col.create_index("email", unique=True)
    users_col.create_index("mobile", unique=True)
    password_resets_col.create_index("expires_at", expireAfterSeconds=3600)  # Auto expire after 1 hour
    tickets_col.create_index("user_id")
    tickets_col.create_index("status")
except Exception as e:
    print(f"Index creation warning: {e}")

def create_support_ticket(user_id, message):
    """Helper function to create a ticket structure"""
    return {
        'user_id': ObjectId(user_id),
        'message': message,
        'response': None,
        'created_at': datetime.utcnow(),
        'status': 'open',
        'user_info': {
            'name': None,
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
        user = users_col.find_one({'email': email})
        
        if user:
            token = secrets.token_urlsafe(32)
            expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            
            password_resets_col.insert_one({
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
    reset_request = password_resets_col.find_one({
        'token': token,
        'expires_at': {'$gt': datetime.now(timezone.utc)}
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
        
        users_col.update_one(
            {'email': reset_request['email']},
            {'$set': {'password': generate_password_hash(password)}}
        )
        
        password_resets_col.delete_one({'token': token})
        
        flash('Password updated successfully! Please login.', 'success')
        return redirect(url_for('user_login'))
    
    return render_template('reset_password.html', token=token)

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('user_login'))
        
        user = users_col.find_one({'email': email, 'role': 'user'})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = 'user'
            session['name'] = user.get('full_name', 'User')
            session['email'] = user.get('email', '')
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
        
        admin = users_col.find_one({'email': email, 'role': 'admin'})
        
        if admin and check_password_hash(admin['password'], password):
            session['user_id'] = str(admin['_id'])
            session['role'] = 'admin'
            session['name'] = admin.get('full_name', 'Admin')
            session['email'] = admin.get('email', '')
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
        
        existing_user = users_col.find_one({'$or': [{'email': email}, {'mobile': mobile}]})
        if existing_user:
            flash('Email or mobile already registered', 'danger')
            return redirect(url_for('user_signup'))
        
        users_col.insert_one({
            'full_name': full_name,
            'email': email,
            'mobile': mobile,
            'password': generate_password_hash(password),
            'role': 'user',
            'created_at': datetime.now(timezone.utc)
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
        confirm_password = request.form.get('confirm_password')
        admin_key = request.form.get('admin_key')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('admin_signup'))
            
        if not all([full_name, email, mobile, password, confirm_password, admin_key]):
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('admin_signup'))
        
        # Validate admin key (you can set this in your environment variables)
        expected_admin_key = os.getenv('ADMIN_REGISTRATION_KEY', 'default-admin-key')
        if admin_key != expected_admin_key:
            flash('Invalid admin registration key', 'danger')
            return redirect(url_for('admin_signup'))
                 
        existing_admin = users_col.find_one({'$or': [{'email': email}, {'mobile': mobile}]})
        if existing_admin:
            flash('Email or mobile already registered', 'danger')
            return redirect(url_for('admin_signup'))
        
        users_col.insert_one({
            'full_name': full_name,
            'email': email,
            'mobile': mobile,
            'password': generate_password_hash(password),
            'role': 'admin',
            'created_at': datetime.now(timezone.utc)
        })
        
        flash('Admin registration successful! Please login.', 'success')
        return redirect(url_for('admin_login'))
    
    return render_template('admin_signup.html')

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/books')
def admin_books():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    query = request.args.get('q', '')
    selected_category = request.args.get('category', '')

    categories = books_col.distinct('type')

    filter_query = {}
    if query:
        filter_query['$or'] = [
            {'title': {'$regex': query, '$options': 'i'}},
            {'author': {'$regex': query, '$options': 'i'}}
        ]
    if selected_category:
        filter_query['type'] = selected_category

    books = list(books_col.find(filter_query))
    return render_template('books.html', books=books, categories=categories)

@app.route('/admin/add-book', methods=['GET', 'POST'])
def add_book():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    if request.method == 'POST':
        new_book = {
            'title': request.form['title'],
            'author': request.form['author'],
            'type': request.form['type'],
            'price': float(request.form['price']),
            'image': request.form['image'],
            'created_at': datetime.now(timezone.utc)
        }
        books_col.insert_one(new_book)
        flash('Book added successfully!', 'success')
        return redirect(url_for('admin_books'))
    return render_template('add_book.html')

@app.route('/admin/edit-book/<book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    book = books_col.find_one({'_id': ObjectId(book_id)})
    if not book:
        flash('Book not found', 'danger')
        return redirect(url_for('admin_books'))
        
    if request.method == 'POST':
        updated_book = {
            'title': request.form['title'],
            'author': request.form['author'],
            'type': request.form['type'],
            'price': float(request.form['price']),
            'image': request.form['image'],
            'updated_at': datetime.now(timezone.utc)
        }
        books_col.update_one({'_id': ObjectId(book_id)}, {'$set': updated_book})
        flash('Book updated successfully!', 'success')
        return redirect(url_for('admin_books'))
    return render_template('edit_book.html', book=book)

@app.route('/admin/delete-book/<book_id>')
def delete_book(book_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    books_col.delete_one({'_id': ObjectId(book_id)})
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('admin_books'))

@app.route('/admin/borrowed-books')
def borrowed_books():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    borrowed_books_list = list(borrowed_books_col.find())
    return render_template('borrowed_books.html', borrowed_books=borrowed_books_list)

@app.route("/admin/add-borrowed-book", methods=["GET", "POST"])
def add_borrowed_book():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    if request.method == "POST":
        borrowed_books_col.insert_one({
            "student_name": request.form['student_name'],
            "student_id": request.form['student_id'],
            "year": request.form['year'],
            "book_title": request.form['book_title'],
            "borrow_date": request.form['borrow_date'],
            "status": request.form['status'],
            "created_at": datetime.now(timezone.utc)
        })
        flash('Borrowed book record added successfully!', 'success')
        return redirect(url_for('borrowed_books'))

    return render_template("add_borrowed_book.html")

@app.route("/admin/edit-borrowed-book/<id>", methods=["GET", "POST"])
def edit_borrowed_book(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    entry = borrowed_books_col.find_one({"_id": ObjectId(id)})
    if not entry:
        flash('Record not found', 'danger')
        return redirect(url_for('borrowed_books'))

    if request.method == "POST":
        updated_entry = {
            "student_name": request.form['student_name'],
            "student_id": request.form['student_id'],
            "year": request.form['year'],
            "book_title": request.form['book_title'],
            "borrow_date": request.form['borrow_date'],
            "status": request.form['status'],
            "updated_at": datetime.now(timezone.utc)
        }

        borrowed_books_col.update_one({"_id": ObjectId(id)}, {"$set": updated_entry})
        flash('Borrowed book record updated successfully!', 'success')
        return redirect(url_for('borrowed_books'))

    return render_template("edit_borrowed_book.html", entry=entry)

@app.route("/admin/delete-borrowed-book/<id>")
def delete_borrowed_book(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    borrowed_books_col.delete_one({"_id": ObjectId(id)})
    flash('Borrowed book record deleted successfully!', 'success')
    return redirect(url_for('borrowed_books'))

@app.route('/admin/categories')
def categories():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    category_data = list(books_col.aggregate(pipeline))
    return render_template('categories.html', categories=category_data)

# USER PAGE ROUTES
@app.route('/user/books')
def user_books():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('user_login'))
        
    query = request.args.get('q', '')
    category = request.args.get('category', '')

    filter_query = {}
    if query:
        filter_query['$or'] = [
            {'title': {'$regex': query, '$options': 'i'}},
            {'author': {'$regex': query, '$options': 'i'}}
        ]
    if category:
        filter_query['type'] = category

    books = list(books_col.find(filter_query))
    categories = books_col.distinct("type")

    return render_template('user_books.html', books=books, categories=categories, query=query)

@app.route('/support')
def user_support():
    if 'user_id' not in session or session['role'] != 'user':
        flash('Please login to access support', 'warning')
        return redirect(url_for('user_login'))
    
    tickets = list(tickets_col.find({
        'user_id': ObjectId(session['user_id'])
    }).sort('created_at', -1))
    
    return render_template('user_support.html', tickets=tickets)

@app.route('/submit-ticket', methods=['POST'])
def submit_ticket():
    if 'user_id' not in session or session['role'] != 'user':
        flash('Please login to submit a ticket', 'warning')
        return redirect(url_for('user_login'))
    
    issue_type = request.form.get('issue_type')
    description = request.form.get('description')
    
    if not issue_type or not description:
        flash('Please fill all required fields', 'danger')
        return redirect(url_for('user_support'))
    
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
        tickets_col.insert_one(ticket_data)
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
    
    tickets = list(tickets_col.aggregate([
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
    
    tickets_col.update_one(
        {'_id': ObjectId(ticket_id)},
        {'$set': {
            'status': 'resolved',
            'resolution': resolution,
            'resolved_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }}
    )
    
    flash('Ticket resolved successfully', 'success')
    return redirect(url_for('admin_support'))

if __name__ == '__main__':
    app.run(debug=True)