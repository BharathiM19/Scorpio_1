from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector

app = Flask(__name__)
app.config['SECRET_KEY'] = '12345'  # Change this to a strong secret key

# 🟢 Database Connection Function
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="12345",  # Change this to your MySQL password
            database="database_healthcare",
            port=3307
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Database Connection Error: {e}")
        return None  # Avoids breaking the app if DB connection fails

bcrypt = Bcrypt(app)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 🟢 User Model (For Flask-Login)
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return User(user["id"], user["username"], user["role"])
    return None

# 🟢 Home Route
@app.route('/')
def home():
    return redirect(url_for('login'))

# 🟢 Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            conn.close()

            if user and bcrypt.check_password_hash(user['password'], password):
                login_user(User(user['id'], user['username'], user['role']))
                flash('Login successful!', 'success')

                print(f"User logged in: {user['username']}, Role: {user['role']}")  # Debugging Output

                # ✅ Redirect based on role
                if user['role'] == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                elif user['role'] == 'patient':
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid role detected!', 'danger')
                    return redirect(url_for('home'))
            else:
                flash('Invalid credentials', 'danger')
        else:
            flash('Database connection failed!', 'danger')

    return render_template('login.html')

# 🟢 Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# 🟢 Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        role = request.form['role']  # "patient" or "doctor"

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
            conn.commit()
            conn.close()

            flash('Registration successful! Please log in.', 'success')

            print(f"New user registered: {username}, Role: {role}")  # Debugging Output

            return redirect(url_for('login'))
        else:
            flash('Database connection failed!', 'danger')

    return render_template('register.html')

# 🟢 Patient Dashboard (Now Displays User Info)
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'patient':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('home'))

    # Pass user details to the dashboard
    return render_template('dashboard.html', user=current_user)

# 🟢 Doctor Dashboard (Now Displays User Info)
@app.route('/doctor-dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('home'))

    # Pass user details to the doctor dashboard
    return render_template('doctor-dashboard.html', user=current_user)

if __name__ == '__main__':
    app.run(debug=True)
