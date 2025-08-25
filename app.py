from flask import Flask, render_template, request, redirect
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import mysql.connector
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask_mail import Mail, Message
import random


app = Flask(__name__)
app.secret_key = "your_secret_key"
# Flask-Mail configuration (use Gmail for example)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'      # replace with your Gmail
app.config['MAIL_PASSWORD'] = 'your_app_password'         # use app password, not real password

mail = Mail(app)
   # you can put any random string here


# ---------------------------
# Database Connection
# ---------------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",              # ⚡ change this if you created another MySQL user
    password="admin123",  # ⚡ replace with your MySQL password
    database="student_results"
)

# ---------------------------
# Teacher Login
# ---------------------------
@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin123":
            session['teacher_id'] = 1
            return redirect(url_for('index'))   # ✅ FIXED
        else:
            return render_template('teacher_login.html', error="Invalid Credentials")
    
    return render_template('teacher_login.html')


# ---------------------------
# Dashboard/Homepage
# ---------------------------


# ---------------------------
# Login Route
# ---------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']

        cursor = db.cursor()
        cursor.execute("SELECT * FROM Students WHERE name=%s AND roll_no=%s", (name, roll_no))
        student = cursor.fetchone()

        if student:
            session['student_id'] = student[0]  # store student id in session
            return redirect(url_for('result', student_id=student[0]))
        else:
            return "❌ Invalid Name or Roll No. Please try again."

    return render_template('login.html')

@app.route('/')
def home():
    return render_template('login_choice.html')
@app.route('/index')
def index():
    if 'teacher_id' not in session:   # only teacher can access
        return redirect(url_for('teacher_login'))

    cursor = db.cursor()

    # Fetch all students
    cursor.execute("SELECT * FROM Students")
    students = cursor.fetchall()

    # Dashboard stats
    cursor.execute("SELECT COUNT(*) FROM Students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Subjects")
    total_subjects = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(attendance) FROM Students")
    avg_attendance = round(cursor.fetchone()[0] or 0, 2)

    return render_template(
        'index.html',
        students=students,
        total_students=total_students,
        total_subjects=total_subjects,
        avg_attendance=avg_attendance
    )


# ---------------------------
# Add Student
# ---------------------------
@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'teacher' not in session:   # only teacher can access
        return redirect(url_for('teacher_login'))

    cursor = db.cursor()

    # Fetch all students
    cursor.execute("SELECT * FROM Students")
    students = cursor.fetchall()

    # Dashboard stats
    cursor.execute("SELECT COUNT(*) FROM Students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Subjects")
    total_subjects = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(attendance) FROM Students")
    avg_attendance = round(cursor.fetchone()[0] or 0, 2)

    return render_template(
        'index.html',
        students=students,
        total_students=total_students,
        total_subjects=total_subjects,
        avg_attendance=avg_attendance
    )

# ---------------------------
# Add Marks for a Student
# ---------------------------
@app.route('/add_marks/<int:student_id>', methods=['GET', 'POST'])
def add_marks(student_id):
    cursor = db.cursor()

    # Get all subjects
    cursor.execute("SELECT * FROM Subjects")
    subjects = cursor.fetchall()

    if 'teacher' not in session:   # only teacher can access
        return redirect(url_for('teacher_login'))

    cursor = db.cursor()

    # Fetch all students
    cursor.execute("SELECT * FROM Students")
    students = cursor.fetchall()

    # Dashboard stats
    cursor.execute("SELECT COUNT(*) FROM Students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Subjects")
    total_subjects = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(attendance) FROM Students")
    avg_attendance = round(cursor.fetchone()[0] or 0, 2)

    return render_template(
        'index.html',
        students=students,
        total_students=total_students,
        total_subjects=total_subjects,
        avg_attendance=avg_attendance
    )

# ---------------------------
# View Result
# ---------------------------
@app.route('/result/<int:student_id>')
def result(student_id):
    cursor = db.cursor()

    # Fetch student details
    cursor.execute("SELECT * FROM Students WHERE student_id=%s", (student_id,))
    student = cursor.fetchone()

    # Fetch marks with subject names
    cursor.execute("""
        SELECT s.subject_name, m.marks_obtained 
        FROM Marks m 
        JOIN Subjects s ON m.subject_id = s.subject_id
        WHERE m.student_id=%s
    """, (student_id,))
    marks = cursor.fetchall()

    # Calculate total & grade
    total_marks = sum([m[1] for m in marks]) if marks else 0
    grade = 'F'
    if total_marks >= 400:  # assuming 5 subjects, max 500
        grade = 'A'
    elif total_marks >= 300:
        grade = 'B'
    elif total_marks >= 200:
        grade = 'C'

    # Insert/Update result
    cursor.execute("SELECT * FROM Results WHERE student_id=%s", (student_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE Results SET total_marks=%s, grade=%s WHERE student_id=%s",
            (total_marks, grade, student_id)
        )
    else:
        cursor.execute(
            "INSERT INTO Results (student_id, total_marks, grade) VALUES (%s, %s, %s)",
            (student_id, total_marks, grade)
        )
    db.commit()

    # Fetch final result
    cursor.execute("SELECT * FROM Results WHERE student_id=%s", (student_id,))
    result = cursor.fetchone()

    return render_template('result.html', student=student, marks=marks, result=result)

# ---------------------------
# Download Result as PDF
# ---------------------------
@app.route('/download_pdf/<int:student_id>')
def download_pdf(student_id):
    cursor = db.cursor()

    cursor.execute("SELECT * FROM Students WHERE student_id=%s", (student_id,))
    student = cursor.fetchone()

    cursor.execute("""
        SELECT s.subject_name, m.marks_obtained 
        FROM Marks m 
        JOIN Subjects s ON m.subject_id = s.subject_id
        WHERE m.student_id=%s
    """, (student_id,))
    marks = cursor.fetchall()

    cursor.execute("SELECT * FROM Results WHERE student_id=%s", (student_id,))
    result = cursor.fetchone()

    # Create PDF
    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
    pdf.setTitle("Student Result")

    pdf.drawString(200, 750, "Student Result Report")
    pdf.line(50, 740, 550, 740)

    pdf.drawString(50, 700, f"Name: {student[1]}")
    pdf.drawString(50, 680, f"Roll No: {student[2]}")
    pdf.drawString(50, 660, f"Class: {student[3]}")
    pdf.drawString(50, 640, f"Attendance: {student[4]}%")

    y = 600
    pdf.drawString(50, y, "Subjects and Marks:")
    y -= 20
    for m in marks:
        pdf.drawString(70, y, f"{m[0]}: {m[1]}")
        y -= 20

    pdf.drawString(50, y-20, f"Total Marks: {result[2]}")
    pdf.drawString(50, y-40, f"Grade: {result[3]}")

    pdf.showPage()
    pdf.save()
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True, download_name="result.pdf", mimetype='application/pdf')

# ---------------------------
# Logout Routes
# ---------------------------
@app.route('/teacher_logout')
def teacher_logout():
    session.pop('teacher_id', None)   # remove teacher session
    return redirect(url_for('teacher_login'))

@app.route('/student_logout')
def student_logout():
    session.pop('student_id', None)  # remove student session
    return redirect(url_for('login'))

# ---------------------------
# Login & Logout Choice Pages
# ---------------------------
@app.route('/login_choice')
def login_choice():
    return render_template('login_choice.html')

@app.route('/logout_choice')
def logout_choice():
    return render_template('logout_choice.html')

# Store OTP temporarily
otp_storage = {}

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        # generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        otp_storage[email] = otp

        # send email
        msg = Message('Password Reset OTP - Student Result System',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[email])
        msg.body = f"Your OTP for password reset is: {otp}"
        mail.send(msg)

        return render_template('verify_otp.html', email=email)

    return render_template('forgot_password.html')


@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email = request.form['email']
    entered_otp = request.form['otp']
    new_password = request.form['new_password']

    if email in otp_storage and otp_storage[email] == entered_otp:
        cursor = db.cursor()
        cursor.execute("UPDATE Teachers SET password=%s WHERE email=%s", (new_password, email))
        db.commit()

        otp_storage.pop(email)  # remove OTP after use
        return "✅ Password updated successfully! <a href='/teacher_login'>Login here</a>"
    else:
        return "❌ Invalid OTP! <a href='/forgot_password'>Try again</a>"



# ---------------------------
# Run Flask App
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
