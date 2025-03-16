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
        return None

bcrypt = Bcrypt(app)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 🟢 User Model
class User(UserMixin):
    def __init__(self, id, username, role, doctor_id=None):
        self.id = id
        self.username = username
        self.role = role
        self.doctor_id = doctor_id  # Only for doctors

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return User(user["id"], user["username"], user["role"], user.get("doctor_id"))
    return None

# 🟢 Home Route
@app.route('/')
def home():
    return redirect(url_for('login'))

# 🟢 Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role'].strip().lower()

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)

            if role == "doctor":
                doctor_id = request.form['doctorId'].strip().upper()
                print(f"🔵 Doctor trying to login with ID: {doctor_id}")  # Debugging

                cursor.execute("SELECT * FROM users WHERE doctor_id = %s AND role = 'doctor'", (doctor_id,))
                user = cursor.fetchone()

                if user:
                    print(f"✅ Found Doctor in DB with ID: {user['doctor_id']}")  # Debugging
                else:
                    print(f"❌ No matching doctor ID found in DB!")  # Debugging
            else:
                username = request.form['username'].strip().lower()
                password = request.form['password']
                cursor.execute("SELECT * FROM users WHERE username = %s AND role = 'patient'", (username,))
                user = cursor.fetchone()

            conn.close()

            if user:
                if role == "doctor":
                    login_user(User(user['id'], user['username'], user['role'], user['doctor_id']))
                    flash(f'Doctor {user["username"]} logged in successfully!', 'success')
                    return redirect(url_for('doctor_dashboard'))
                
                elif role == "patient" and bcrypt.check_password_hash(user['password'], password):
                    login_user(User(user['id'], user['username'], user['role']))
                    flash('Patient login successful!', 'success')
                    return redirect(url_for('dashboard'))
                
                else:
                    flash('Invalid credentials!', 'danger')
            else:
                flash('User not found!', 'danger')

    return render_template('login.html')

# 🟢 Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# 🟢 Registration Route (Doctors Use Auto-Generated ID)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        role = request.form.get('role').strip().lower()

        if role not in ["doctor", "patient"]:
            flash('Invalid role selection!', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)

            # 🛑 CHECK IF USERNAME ALREADY EXISTS
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Username already exists! Choose a different one.', 'danger')
                conn.close()
                return redirect(url_for('register'))

            # ✅ Process doctor_id for doctors
            doctor_id = None
            if role == "doctor":
                doctor_id = request.form['doctorId'].strip().upper()  # Ensure uppercase & no spaces
                
                if not doctor_id:
                    flash('Doctor ID is missing!', 'danger')
                    conn.close()
                    return redirect(url_for('register'))

                # Check if doctor_id already exists
                cursor.execute("SELECT * FROM users WHERE doctor_id = %s", (doctor_id,))
                existing_doctor = cursor.fetchone()
                if existing_doctor:
                    flash('Doctor ID already exists! Please try again with a new ID.', 'danger')
                    conn.close()
                    return redirect(url_for('register'))

            # ✅ INSERT NEW USER
            cursor.execute("""
                INSERT INTO users (username, password, role, doctor_id) 
                VALUES (%s, %s, %s, %s)
            """, (username, password, role, doctor_id))
            conn.commit()

            conn.close()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Database connection failed!', 'danger')

    return render_template('register.html')

# 🟢 Patient Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'patient':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('home'))

    return render_template('dashboard.html', user=current_user)

# 🟢 Doctor Dashboard
@app.route('/doctor-dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('home'))

    return render_template('doctor-dashboard.html', user=current_user, doctor_id=current_user.doctor_id)

if __name__ == '__main__':
    app.run(debug=True)