from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pymysql
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = '12345'  # Change this to a strong secret key
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 🟢 Database Connection Function (Updated for PyMySQL)
def get_db_connection():
    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="root123",  # Updated MySQL password
            database="database_healthcare",
            port=3306,
            cursorclass=pymysql.cursors.DictCursor  # Use dictionary cursor
        )
        return conn
    except pymysql.MySQLError as e:
        print(f"Database Connection Error: {e}")
        return None

bcrypt = Bcrypt(app)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 🟢 User Model
class User(UserMixin):
    def __init__(self, id, username, role, doctor_id=None, gender=None, dob=None, phone=None, blood_group=None):
        self.id = id
        self.username = username
        self.role = role
        self.doctor_id = doctor_id  # Only for doctors
        # Additional patient info
        self.gender = gender
        self.dob = dob
        self.phone = phone
        self.blood_group = blood_group

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
        conn.close()
        if user:
            return User(
                user["id"], 
                user["username"], 
                user["role"], 
                user.get("doctor_id"),
                user.get("gender"),
                user.get("dob"),
                user.get("phone"),
                user.get("blood_group")
            )
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
            with conn.cursor() as cursor:
                if role == "doctor":
                    doctor_id = request.form['doctorId'].strip().upper()
                    cursor.execute("SELECT * FROM users WHERE doctor_id = %s AND role = 'doctor'", (doctor_id,))
                else:
                    username = request.form['username'].strip().lower()
                    password = request.form['password']
                    cursor.execute("SELECT * FROM users WHERE username = %s AND role = 'patient'", (username,))

                user = cursor.fetchone()

            conn.close()

            if user:
                if role == "doctor":
                    login_user(User(
                        user['id'], 
                        user['username'], 
                        user['role'], 
                        user['doctor_id']
                    ))
                    flash(f'Doctor {user["username"]} logged in successfully!', 'success')
                    return redirect(url_for('doctor_dashboard'))
                
                elif role == "patient" and bcrypt.check_password_hash(user['password'], password):
                    login_user(User(
                        user['id'], 
                        user['username'], 
                        user['role'],
                        None,
                        user.get('gender'),
                        user.get('dob'),
                        user.get('phone'),
                        user.get('blood_group')
                    ))
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
    return redirect(url_for('login'))

# 🟢 Registration Route
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
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                existing_user = cursor.fetchone()

                if existing_user:
                    flash('Username already exists! Choose a different one.', 'danger')
                    return redirect(url_for('register'))

                doctor_id = None
                if role == "doctor":
                    doctor_id = request.form['doctorId'].strip().upper()
                    cursor.execute("SELECT * FROM users WHERE doctor_id = %s", (doctor_id,))
                    existing_doctor = cursor.fetchone()
                    if existing_doctor:
                        flash('Doctor ID already exists! Please try again with a new ID.', 'danger')
                        return redirect(url_for('register'))

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
        return redirect(url_for('login'))

    return render_template('dashboard.html', user=current_user)

# 🟢 Doctor Dashboard
@app.route('/doctor-dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    return render_template('doctor-dashboard.html', user=current_user)

# 🟢 Add Operation/Treatment Route for Patient
@app.route('/add_operation', methods=['POST'])
@login_required
def add_operation():
    if current_user.role != 'patient':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        doctor_name = request.form['doctor_name']
        hospital_name = request.form['hospital_name']
        patient_name = request.form['patient_name']
        patient_age = request.form['patient_age']
        operation_names = request.form['operation_names']
        operation_date = request.form['operation_date']
        description = request.form['description']
        
        # Handle file uploads if present
        files_uploaded = ""
        prescription_file = ""
        
        if 'files_uploaded' in request.files:
            files = request.files.getlist('files_uploaded')
            file_paths = []
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    new_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                    file.save(file_path)
                    file_paths.append(new_filename)
            files_uploaded = ",".join(file_paths)
        
        if 'prescription_file' in request.files and request.files['prescription_file'].filename:
            file = request.files['prescription_file']
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_filename = f"prescription_{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(file_path)
            prescription_file = new_filename
        
        # Save to database (patient_id removed to match the table schema)
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO operation_treatment_info 
                        (doctor_name, hospital_name, patient_name, patient_age, operation_names, 
                        files_uploaded, operation_date, description, prescription_file) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        doctor_name, hospital_name, patient_name, patient_age, operation_names,
                        files_uploaded, operation_date, description, prescription_file
                    ))
                    conn.commit()
                    
                flash('Treatment information added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding treatment information: {e}', 'danger')
            finally:
                conn.close()
        else:
            flash('Database connection failed!', 'danger')
        
        return redirect(url_for('dashboard'))

# 🟢 Search Patient API for Doctor Dashboard
@app.route('/search_patient', methods=['POST'])
@login_required
def search_patient():
    if current_user.role != 'doctor':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    patient_id = request.form.get('patient_id')
    if not patient_id:
        return jsonify({'error': 'Patient ID is required'}), 400
    
    conn = get_db_connection()
    if conn:
        try:
            # Get patient details
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, gender, dob, phone, blood_group 
                    FROM users WHERE id = %s AND role = 'patient'
                """, (patient_id,))
                patient = cursor.fetchone()
            
            if not patient:
                return jsonify({'error': 'Patient not found'}), 404
            
            # Calculate age from DOB if available
            age = None
            if patient.get('dob'):
                dob = datetime.strptime(patient['dob'], '%Y-%m-%d')
                today = datetime.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            # Fetch treatment history by matching the patient name
            treatments = []
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM operation_treatment_info
                    WHERE patient_name = %s
                    ORDER BY operation_date DESC
                """, (patient['username'],))
                treatments = cursor.fetchall()
            
            # Convert datetime objects to strings for JSON serialization
            for treatment in treatments:
                if 'operation_date' in treatment and treatment['operation_date']:
                    treatment['operation_date'] = treatment['operation_date'].strftime('%Y-%m-%d')
            
            return jsonify({
                'patient': {
                    'id': patient['id'],
                    'name': patient['username'],
                    'gender': patient.get('gender'),
                    'dob': patient.get('dob'),
                    'phone': patient.get('phone'),
                    'blood_group': patient.get('blood_group'),
                    'age': age
                },
                'treatments': treatments
            })
        except Exception as e:
            return jsonify({'error': f'Error fetching patient data: {e}'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': 'Database connection failed'}), 500

# 🟢 Add Treatment by Doctor
@app.route('/add_treatment', methods=['POST'])
@login_required
def add_treatment():
    if current_user.role != 'doctor':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    doctor_name = request.form.get('doctor_name')
    hospital_name = request.form.get('hospital_name')
    if hospital_name == 'Other' and 'other_hospital_name' in request.form:
        hospital_name = request.form.get('other_hospital_name')
    
    patient_name = request.form.get('patient_name')
    patient_age = request.form.get('patient_age')
    operation_names = request.form.get('operation_names')
    operation_date = request.form.get('operation_date')
    description = request.form.get('description')
    prescription = request.form.get('prescription')
    
    # Save to database (patient_id removed)
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO operation_treatment_info 
                    (doctor_name, hospital_name, patient_name, patient_age, operation_names, 
                    operation_date, description, prescription_file) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    doctor_name, hospital_name, patient_name, patient_age, operation_names,
                    operation_date, description, prescription
                ))
                conn.commit()
                
                return jsonify({'success': 'Treatment added successfully'})
        except Exception as e:
            return jsonify({'error': f'Error adding treatment: {e}'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': 'Database connection failed'}), 500

if __name__ == '__main__':
    app.run(debug=True)