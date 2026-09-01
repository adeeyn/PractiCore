from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates')
app.secret_key = "nyek"

# MySQL Configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'practicore'
}

def get_db():
    """Helper function to obtain a fresh MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)

@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM students WHERE username = %s",
            (username,)
        )
        record = cursor.fetchone()
        cursor.close()
        db.close()

        # Check if user exists and verify hashed password (or plain text fallback if migrated)
        if record:
            stored_password = record.get("password_hash") or record.get("password")
            is_valid = False
            
            if stored_password:
                if stored_password.startswith("pbkdf2:") or stored_password.startswith("scrypt:"):
                    is_valid = check_password_hash(stored_password, password)
                else:
                    is_valid = (stored_password == password)

            if is_valid:
                session["loggedin"] = True
                session["username"] = record.get("username")
                session["studentNo"] = record.get("student_no") or record.get("studentNo")

                return redirect(url_for("student_dashboard"))

        failed_username = request.args.get("username", "")
        return render_template("student_login.html", failed=1, username=failed_username)

    return render_template("student_login.html", failed=0, username="")



@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        # 1. Extract inputs matching student_register.html form names
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        student_no = request.form.get('studentNo', '').strip()
        phone = request.form.get('phone', '').strip()
        year_level = request.form.get('year_level', '4th Year').strip()
        course = request.form.get('course', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirmPassword', '').strip()

        # 2. Validation Checks
        if not all([name, email, username, student_no, course, password, confirm_password]):
            return render_template('student_register.html', error="Please fill out all required fields.")

        if password != confirm_password:
            return render_template('student_register.html', error="Passwords do not match.")

        # 3. Hash the password
        hashed_password = generate_password_hash(password)

        # 4. Save to MySQL Database
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)

            # Check for existing student_no, username, or email
            cursor.execute(
                "SELECT id FROM students WHERE student_no = %s OR username = %s OR email = %s",
                (student_no, username, email)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.close()
                db.close()
                return render_template('student_register.html', error="Student Number, Username, or Email already exists.")

            # Insert new record into MySQL students table
            cursor.execute("""
                INSERT INTO students (name, email, username, student_no, phone, year_level, course, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, email, username, student_no, phone, year_level, course, hashed_password))

            db.commit()
            cursor.close()
            db.close()

            return redirect(url_for('student_login'))

        except mysql.connector.Error as err:
            return render_template('student_register.html', error=f"Database error: {err}")

    # GET request - Display the form
    return render_template('student_register.html')

@app.route("/student_dashboard")
def student_dashboard():
    if 'loggedin' not in session:
        return redirect(url_for("student_login"))

    return render_template(
        "student_dashboard.html",
        username=session.get('username'),
        active_page='dashboard'  # Add this explicit active_page parameter
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("student_login"))

@app.route('/student_profile')
def student_profile():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))
    
    return render_template('student_profile.html', active_page='profile')

@app.route('/upload_resume')
def upload_resume():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))
    
    return render_template('upload_resume.html', active_page='resume')

@app.route('/assessment')
def assessment():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))

    return render_template('assessment.html', active_page='assessment')

@app.route('/recommendation')
def recommendation():
    if 'loggedin' not in session:
        return redirect(url_for('student_login'))
        
    return render_template('recommendation.html', active_page='recommendation')

@app.route('/application')
def application():
    if 'loggedin' not in session:
        return redirect(url_for('application'))
        
    return render_template('application.html', active_page='application')

if __name__ == "__main__":
    app.run(debug=True)