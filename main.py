from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USER_FILE = './data/users.json'
MEALS_FILE = './data/meals.json'
FOOD_DB_FILE = './data/food_db.json'

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_meals():
    if os.path.exists(MEALS_FILE):
        with open(MEALS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_meals(meals):
    with open(MEALS_FILE, 'w') as f:
        json.dump(meals, f, indent=4)

def load_food_db():
    if os.path.exists(FOOD_DB_FILE):
        with open(FOOD_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        age = request.form['age']
        weight = float(request.form['weight'])
        height = float(request.form['height'])
        gender = request.form['gender']
        goal = request.form['goal']

        users = load_users()
        if email in users:
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for('login'))

        users[email] = {
            'name': name,
            'password': generate_password_hash(password),
            'age': age,
            'weight': weight,
            'height': height,
            'gender': gender,
            'goal': goal
        }
        save_users(users)
        session['email'] = email
        flash("Registration successful. Welcome to your dashboard!", "success")
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        users = load_users()
        user = users.get(email)

        if user and check_password_hash(user['password'], password):
            session['email'] = email
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_email = session['email']
    users = load_users()
    user_data = users.get(user_email)
    if not user_data:
        flash("User not found.", "danger")
        return redirect(url_for('logout'))

    meals = load_meals()
    food_db = load_food_db()

    user_meals = []
    for m in meals:
        if m['user'] == user_email:
            try:
                m['loggedAt'] = datetime.strptime(m['loggedAt'], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            user_meals.append(m)
    def calculate_bmr(gender, weight, height, age):
        if gender.lower() == 'male':
            return 88.362 + 13.397 * weight + 4.799 * height - 5.677 * age
        else:
            return 447.593 + 9.247 * weight + 3.098 * height - 4.33 * age
            
    bmr = calculate_bmr(
        gender=user_data['gender'],
        weight=float(user_data['weight']),
        height=float(user_data['height']),
        age=int(user_data['age'])
    )

    return render_template(
        'dashboard.html',
        user=user_data['name'],
        details=user_data,
        bmr=round(bmr),
        meals=user_meals,
        food_db=food_db
    )

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    email = session['email']
    users = load_users()
    user = users[email]

    user['name'] = request.form['name']
    user['age'] = request.form['age']
    user['weight'] = float(request.form['weight'])
    user['height'] = float(request.form['height'])
    user['gender'] = request.form['gender']
    user['goal'] = request.form['goal']

    save_users(users)
    flash('Profile updated successfully.', 'success')
    return redirect('/dashboard')

@app.route('/delete_profile', methods=['POST'])
@login_required
def delete_profile():
    email = session['email']
    users = load_users()
    users.pop(email, None)
    save_users(users)
    session.clear()
    flash('Your profile has been deleted.', 'warning')
    return redirect('/signup')

@app.route('/log_meal', methods=['GET', 'POST'])
@login_required
def log_meal():
    meals = load_meals()
    food_db = load_food_db()

    if request.method == 'POST':
        meal_type = request.form['meal']
        items = request.form.getlist('items')
        user_email = session['email']
        log_entry = {
            "user": user_email,
            "meal": meal_type,
            "items": items,
            "loggedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        meals.append(log_entry)
        save_meals(meals)
        flash("Meal logged successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('log_meal.html', food_db=food_db)

@app.route('/meal_summary')
@login_required
def meal_summary():
    meals = load_meals()
    food_db = load_food_db()
    user_email = session['email']
    today = datetime.now().strftime("%Y-%m-%d")
    user_meals = [m for m in meals if m['user'] == user_email and m['loggedAt'] == today]

    summary = {"calories": 0, "protein": 0, "carbs": 0, "fiber": 0}
    for meal in user_meals:
        for item in meal['items']:
            data = food_db.get(item, {})
            for key in summary:
                summary[key] += data.get(key, 0)

    return render_template('meal_summary.html', meals=user_meals, summary=summary, food_db=food_db)


if __name__ == '__main__':
    app.run(debug=True)
