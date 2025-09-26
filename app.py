from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import secrets
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')

# MongoDB Configuration
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/library_management')
client = MongoClient(MONGODB_URI)
db = client.get_database()

# Collections
books_collection = db.books
users_collection = db.users
borrowed_books_collection = db.borrowed_books
tickets_collection = db.tickets
password_resets_collection = db.password_resets

# Initialize collections with sample data if empty
def initialize_database():
    try:
        if books_collection.count_documents({}) == 0:
            sample_books = [
                {'title': 'Sample Book 1', 'author': 'Author 1', 'type': 'Fiction', 'price': 29.99, 'image': '/static/images/book1.jpg'},
                {'title': 'Sample Book 2', 'author': 'Author 2', 'type': 'Science', 'price': 39.99, 'image': '/static/images/book2.jpg'}
            ]
            books_collection.insert_many(sample_books)
            print("Database initialized with sample data")
    except Exception as e:
        print(f"Database initialization error: {e}")

# Initialize database on app startup
initialize_database()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# ===== PASSWORD RESET ROUTES =====
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = users_collection.find_one({'email': email})
        
        if user:
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(hours=1)
            
            password_resets_collection.insert_one({
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
    reset_request = password_resets_collection.find_one({
        'token': token,
        'expires_at': {'$gt': datetime.utcnow()}
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
        
        users_collection.update_one(
            {'email': reset_request['email']},
            {'$set': {'password': generate_password_hash(password)}}
        )
        
        password_resets_collection.delete_one({'token': token})
        
        flash('Password updated successfully! Please login.', 'success')
        return redirect(url_for('user_login'))
    
    return render_template('reset_password.html', token=token)

# ===== LOGIN ROUTES =====
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

# ===== SIGNUP ROUTES =====
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
        
        existing_admin = users_collection.find_one({'$or': [{'email': email}, {'mobile': mobile}]})
        if existing_admin:
            flash('Email or mobile already registered', 'danger')
            return redirect(url_for('admin_signup'))
        
        users_collection.insert_one({
            'full_name': full_name,
            'email': email,
            'mobile': mobile,
            'password': generate_password_hash(password),
            'role': 'admin',
            'created_at': datetime.utcnow()
        })
        
        flash('Admin registration successful! Please login.', 'success')
        return redirect(url_for('admin_login'))
    
    return render_template('admin_signup.html')

# ===== DASHBOARD ROUTES =====
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

# ===== BOOK MANAGEMENT ROUTES =====
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

@app.route('/admin/books')
def admin_books():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    
    query = request.args.get('q', '')
    selected_category = request.args.get('category', '')

    categories = books_collection.distinct('type')

    filter_query = {}
    if query:
        filter_query['$or'] = [
            {'title': {'$regex': query, '$options': 'i'}},
            {'author': {'$regex': query, '$options': 'i'}}
        ]
    if selected_category:
        filter_query['type'] = selected_category

    books = list(books_collection.find(filter_query))
    return render_template('admin_books.html', books=books, categories=categories)

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
            'created_at': datetime.utcnow()
        }
        books_collection.insert_one(new_book)
        flash('Book added successfully!', 'success')
        return redirect(url_for('admin_books'))
    return render_template('add_book.html')

@app.route('/admin/edit-book/<book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    book = books_collection.find_one({'_id': ObjectId(book_id)})
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
            'updated_at': datetime.utcnow()
        }
        books_collection.update_one({'_id': ObjectId(book_id)}, {'$set': updated_book})
        flash('Book updated successfully!', 'success')
        return redirect(url_for('admin_books'))
    return render_template('edit_book.html', book=book)

@app.route('/admin/delete-book/<book_id>')
def delete_book(book_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    books_collection.delete_one({'_id': ObjectId(book_id)})
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('admin_books'))

# ===== BORROWED BOOKS ROUTES =====
@app.route('/admin/borrowed-books')
def borrowed_books():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    borrowed_books = list(borrowed_books_collection.find())
    return render_template('borrowed_books.html', borrowed_books=borrowed_books)

@app.route("/admin/add-borrowed-book", methods=["GET", "POST"])
def add_borrowed_book():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    if request.method == "POST":
        borrowed_books_collection.insert_one({
            "student_name": request.form['student_name'],
            "student_id": request.form['student_id'],
            "year": request.form['year'],
            "book_title": request.form['book_title'],
            "borrow_date": request.form['borrow_date'],
            "status": request.form['status'],
            "created_at": datetime.utcnow()
        })
        flash('Borrowed book added successfully!', 'success')
        return redirect(url_for('borrowed_books'))

    return render_template("add_borrowed_book.html")

@app.route("/admin/edit-borrowed-book/<id>", methods=["GET", "POST"])
def edit_borrowed_book(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    entry = borrowed_books_collection.find_one({"_id": ObjectId(id)})
    if not entry:
        flash('Entry not found', 'danger')
        return redirect(url_for('borrowed_books'))

    if request.method == "POST":
        updated_entry = {
            "student_name": request.form['student_name'],
            "student_id": request.form['student_id'],
            "year": request.form['year'],
            "book_title": request.form['book_title'],
            "borrow_date": request.form['borrow_date'],
            "status": request.form['status'],
            "updated_at": datetime.utcnow()
        }
        borrowed_books_collection.update_one({"_id": ObjectId(id)}, {"$set": updated_entry})
        flash('Borrowed book updated successfully!', 'success')
        return redirect(url_for('borrowed_books'))

    return render_template("edit_borrowed_book.html", entry=entry)

@app.route("/admin/delete-borrowed-book/<id>")
def delete_borrowed_book(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    borrowed_books_collection.delete_one({"_id": ObjectId(id)})
    flash('Borrowed book deleted successfully!', 'success')
    return redirect(url_for('borrowed_books'))

# ===== SUPPORT TICKET ROUTES =====
@app.route('/support')
def user_support():
    if 'user_id' not in session:
        flash('Please login to access support', 'warning')
        return redirect(url_for('user_login'))
    
    tickets = list(tickets_collection.find({
        'user_id': ObjectId(session['user_id'])
    }).sort('created_at', -1))
    
    return render_template('user_support.html', tickets=tickets)

@app.route('/submit-ticket', methods=['POST'])
def submit_ticket():
    if 'user_id' not in session:
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
        'created_at': datetime.utcnow(),
        'resolution': None
    }
    
    tickets_collection.insert_one(ticket_data)
    flash('Support ticket submitted successfully!', 'success')
    return redirect(url_for('user_support'))

@app.route('/admin/support')
def admin_support():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('admin_login'))
    
    tickets = list(tickets_collection.find().sort('created_at', -1))
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
    
    tickets_collection.update_one(
        {'_id': ObjectId(ticket_id)},
        {'$set': {
            'status': 'resolved',
            'resolution': resolution,
            'resolved_at': datetime.utcnow()
        }}
    )
    
    flash('Ticket resolved successfully', 'success')
    return redirect(url_for('admin_support'))

# ===== CATEGORIES ROUTE =====
@app.route('/admin/categories')
def categories():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
        
    pipeline = [
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    category_data = list(books_collection.aggregate(pipeline))
    return render_template('categories.html', categories=category_data)

# ===== LOGOUT ROUTE =====
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('index'))

# Vercel requires this at the bottom
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
