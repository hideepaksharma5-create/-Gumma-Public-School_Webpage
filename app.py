import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_PATH = os.path.join(os.path.dirname(__file__), "gps_gummaDB.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Create uploads directory if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "database",
        "schema.sql"
    )

    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        # Enable WAL once â€” persists in the DB file permanently
        conn.execute("PRAGMA journal_mode=WAL;")
        # Check if tables already exist
        table_check = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()

        if not table_check:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
            print("Database initialised from schema.sql")
        else:
            print("Database already initialised")

        # Ensure stream and subjects columns exist in applications table
        cursor = conn.execute("PRAGMA table_info(applications);")
        existing_cols = {row[1] for row in cursor.fetchall()}
        for col in ["stream", "subjects"]:
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE applications ADD COLUMN {col} TEXT;")
        conn.commit()
    finally:
        conn.close()  # always closes, even if an exception is raised

# Initialize DB on startup
init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_user():
    # Make username and role available in all templates
    return dict(
        current_username=session.get('user'),
        current_role=session.get('role')
    )

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))

    message = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and user["password"] == password:
            session["user"] = user["username"]
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            message = "Invalid Username or Password"

    return render_template("login.html", message=message)

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect(url_for("dashboard"))

    message = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            message = "All fields are required"
        elif password != confirm_password:
            message = "Passwords do not match"
        else:
            conn = get_db()
            existing = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                message = "Username already exists"
            else:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'student')", (username, password))
                user_id = cursor.lastrowid
                # Insert initial unpaid fee
                cursor.execute("INSERT INTO fees (user_id, amount, status) VALUES (?, 5000.0, 'Unpaid')", (user_id,))
                conn.commit()
                conn.close()
                flash("Registration successful! Please login.")
                return redirect(url_for("login"))
            conn.close()

    return render_template("register.html", message=message)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    if session["role"] == "admin":
        # Fetch stats for admin
        total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        pending_apps = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Pending Review'").fetchone()[0]
        approved_apps = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Approved'").fetchone()[0]
        action_apps = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Action Required'").fetchone()[0]
        
        recent_apps = conn.execute("""
            SELECT a.*, u.username 
            FROM applications a 
            JOIN users u ON a.user_id = u.id 
            ORDER BY a.submitted_at DESC LIMIT 5
        """).fetchall()
        conn.close()
        return render_template("dashboard.html", 
                               total=total_apps, 
                               pending=pending_apps, 
                               approved=approved_apps, 
                               action=action_apps,
                               recent_applications=recent_apps)
    else:
        # Fetch user application status
        app_entry = conn.execute("SELECT * FROM applications WHERE user_id = ?", (session["user_id"],)).fetchone()
        fee_entry = conn.execute("SELECT * FROM fees WHERE user_id = ?", (session["user_id"],)).fetchone()
        conn.close()
        
        # Calculate checklist steps
        checklist = {
            "account": True,
            "profile": app_entry is not None,
            "docs": app_entry is not None and app_entry["tc_filename"] is not None,
            "payment": fee_entry is not None and fee_entry["status"] == "Paid"
        }
        
        return render_template("dashboard.html", 
                               application=app_entry, 
                               fee=fee_entry,
                               checklist=checklist)

@app.route("/admission_form", methods=["GET", "POST"])
def admission_form():
    if "user" not in session or session["role"] == "admin":
        return redirect(url_for("login"))

    conn = get_db()
    existing_app = conn.execute("SELECT * FROM applications WHERE user_id = ?", (session["user_id"],)).fetchone()

    # Pre-extract stream and subjects for editing existing application
    current_stream = ""
    current_subjects = []
    if existing_app:
        try:
            current_stream = existing_app["stream"] or ""
        except (IndexError, KeyError):
            current_stream = ""
        try:
            raw_s = existing_app["subjects"] or ""
            current_subjects = [s.strip() for s in raw_s.split(",") if s.strip()]
        except (IndexError, KeyError):
            current_subjects = []

        # Fallback extraction from grade_applying string if column values are empty
        ga = existing_app["grade_applying"] if "grade_applying" in existing_app.keys() else ""
        if ga:
            if not current_stream:
                if "Arts" in ga:
                    current_stream = "Arts"
                elif "Commerce" in ga:
                    current_stream = "Commerce"
                elif "Non-Medical" in ga:
                    current_stream = "Science (Non-Medical)"
                elif "Medical" in ga:
                    current_stream = "Science (Medical)"
                elif "Science" in ga:
                    current_stream = "Science (Medical)"
            if not current_subjects and "(" in ga and ")" in ga:
                content = ga[ga.find("(") + 1:ga.rfind(")")]
                if ":" in content:
                    content = content.split(":", 1)[1]
                current_subjects = [s.strip() for s in content.split(",") if s.strip()]

    message = ""
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        dob = request.form.get("dob", "")
        gender = request.form.get("gender", "")
        parent_name = request.form.get("parent_name", "").strip()
        parent_email = request.form.get("parent_email", "").strip()
        parent_phone = request.form.get("parent_phone", "").strip()
        grade_applying = request.form.get("grade_applying", "").strip()
        previous_school = request.form.get("previous_school", "").strip()
        stream = request.form.get("stream", "").strip()
        subjects_list = request.form.getlist("subjects")
        subjects_str = ", ".join([s.strip() for s in subjects_list if s.strip()])

        if not student_name or not dob or not gender or not parent_name or not parent_email or not parent_phone or not grade_applying:
            message = "All core fields are required."
        else:
            # Build full grade description with stream & subjects for 11th & 12th
            if grade_applying in ["Class 11", "Class 12"]:
                if stream:
                    if subjects_str:
                        formatted_grade = f"{grade_applying} - {stream} ({subjects_str})"
                    else:
                        formatted_grade = f"{grade_applying} - {stream}"
                else:
                    formatted_grade = grade_applying
            else:
                stream = None
                subjects_str = None
                formatted_grade = grade_applying

            tc_file = request.files.get("tc_file")
            photo_file = request.files.get("photo_file")

            tc_filename = existing_app["tc_filename"] if existing_app else None
            photo_filename = existing_app["photo_filename"] if existing_app else None

            # Handle uploads only after validation passes
            if tc_file and tc_file.filename and allowed_file(tc_file.filename):
                tc_filename = secure_filename(f"tc_{session['user_id']}_{tc_file.filename}")
                tc_file.save(os.path.join(app.config['UPLOAD_FOLDER'], tc_filename))

            if photo_file and photo_file.filename and allowed_file(photo_file.filename):
                photo_filename = secure_filename(f"photo_{session['user_id']}_{photo_file.filename}")
                photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

            if existing_app:
                conn.execute("""
                    UPDATE applications 
                    SET student_name=?, dob=?, gender=?, parent_name=?, parent_email=?, parent_phone=?, 
                        grade_applying=?, stream=?, subjects=?, previous_school=?, tc_filename=?, photo_filename=?, status='Pending Review'
                    WHERE user_id=?
                """, (student_name, dob, gender, parent_name, parent_email, parent_phone, 
                      formatted_grade, stream, subjects_str, previous_school, tc_filename, photo_filename, session["user_id"]))
            else:
                conn.execute("""
                    INSERT INTO applications (user_id, student_name, dob, gender, parent_name, parent_email, 
                                             parent_phone, grade_applying, stream, subjects, previous_school, tc_filename, photo_filename)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (session["user_id"], student_name, dob, gender, parent_name, parent_email, 
                      parent_phone, formatted_grade, stream, subjects_str, previous_school, tc_filename, photo_filename))
            conn.commit()
            conn.close()
            flash("Admission application submitted successfully!")
            return redirect(url_for("dashboard"))

    conn.close()
    return render_template("admission_form.html", 
                           application=existing_app, 
                           current_stream=current_stream, 
                           current_subjects=current_subjects, 
                           message=message)


@app.route("/delete_document", methods=["POST"])
def delete_document():
    if "user" not in session or session["role"] == "admin":
        return redirect(url_for("login"))
    
    field = request.form.get("field")
    allowed_fields = {
        "tc_filename", "photo_filename", "birth_cert_filename",
        "residence_proof_filename", "marksheet_filename", "health_records_filename"
    }
    if field not in allowed_fields:
        flash("Invalid document field.", "error")
        return redirect(url_for("admission_form"))
    
    conn = get_db()
    app_entry = conn.execute("SELECT * FROM applications WHERE user_id = ?", (session["user_id"],)).fetchone()
    
    if app_entry and app_entry[field]:
        # Delete physical file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], app_entry[field])
        if os.path.exists(filepath):
            os.remove(filepath)
        # Clear DB field
        conn.execute(f"UPDATE applications SET {field} = NULL WHERE user_id = ?", (session["user_id"],))
        conn.commit()
        flash("Document deleted successfully.")
    
    conn.close()
    if request.headers.get("Accept") and "application/json" in request.headers.get("Accept"):
        return jsonify({"status": "success", "message": "Document deleted successfully."})
    return redirect(url_for("admission_form"))
@app.route("/students", methods=["GET", "POST"])
def students():
    if "user" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db()
    
    if request.method == "POST":
        app_id = request.form.get("application_id")
        new_status = request.form.get("status")
        comments = request.form.get("comments", "")
        
        conn.execute("UPDATE applications SET status = ?, comments = ? WHERE id = ?", (new_status, comments, app_id))
        conn.commit()
        conn.close()
        flash("Application status updated successfully.")
        return redirect(url_for("students"))
        
    all_students = conn.execute("""
        SELECT a.*, u.username, f.status as fee_status 
        FROM applications a 
        JOIN users u ON a.user_id = u.id
        LEFT JOIN fees f ON u.id = f.user_id
        ORDER BY a.submitted_at DESC
    """).fetchall()
    
    conn.close()
    return render_template("students.html", students=all_students)

@app.route("/fees", methods=["GET", "POST"])
def fees():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    
    if session["role"] == "admin":
        # Show all payments for admin
        all_fees = conn.execute("""
            SELECT f.*, u.username, a.student_name 
            FROM fees f
            JOIN users u ON f.user_id = u.id
            LEFT JOIN applications a ON u.id = a.user_id
            ORDER BY f.payment_date DESC
        """).fetchall()
        conn.close()
        return render_template("fees.html", fees=all_fees)
    else:
        # Student payment
        fee = conn.execute("SELECT * FROM fees WHERE user_id = ?", (session["user_id"],)).fetchone()
        if not fee:
            conn.execute("INSERT INTO fees (user_id, amount, status) VALUES (?, 5000.0, 'Unpaid')", (session["user_id"],))
            conn.commit()
            fee = conn.execute("SELECT * FROM fees WHERE user_id = ?", (session["user_id"],)).fetchone()
        
        if request.method == "POST":
            # Mock payment processing
            transaction_id = request.form.get("transaction_id", "TXN" + os.urandom(4).hex().upper())
            conn.execute("""
                UPDATE fees 
                SET status = 'Paid', transaction_id = ?, payment_date = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            """, (transaction_id, session["user_id"]))
            conn.commit()
            flash("Payment received successfully!")
            conn.close()
            return redirect(url_for("fees"))
            
        conn.close()
        return render_template("fees.html", fee=fee)

@app.route("/status")
def status():
    if "user" not in session or session["role"] == "admin":
        return redirect(url_for("login"))

    conn = get_db()
    app_entry = conn.execute("SELECT * FROM applications WHERE user_id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return render_template("status.html", application=app_entry)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    message = ""
    success = False
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        msg_text = request.form.get("message", "").strip()

        if not name or not email or not msg_text:
            message = "Please fill in all required fields"
        else:
            conn = get_db()
            conn.execute("INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)",
                         (name, email, subject, msg_text))
            conn.commit()
            conn.close()
            flash("Message sent! Our support team will get back to you shortly.")
            return redirect(url_for("contact"))

    return render_template("contact.html", message=message, success=success)

@app.route("/chat", methods=["POST"])
def chat():
    from flask import jsonify
    import json

    data = request.get_json()
    user_msg = data.get("message", "").lower().strip()

    # -----------------------------------------------------------------------
    # Gumma Public School â€” AI Chatbot Knowledge Base
    # -----------------------------------------------------------------------
    SCHOOL_KB = [
        # Greetings
        {
            "triggers": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"],
            "reply": "ðŸ‘‹ Hello! Welcome to **Gumma Public School** Admission Portal. I'm your AI assistant. I can help you with:\n\nâ€¢ ðŸ“‹ Admission process & eligibility\nâ€¢ ðŸ“š Grades & curriculum\nâ€¢ ðŸ’° Fee structure & payments\nâ€¢ ðŸ• School timings & calendar\nâ€¢ ðŸ« Facilities & extracurriculars\nâ€¢ ðŸ“ž Contact information\n\nWhat would you like to know?"
        },
        # Admission process
        {
            "triggers": ["admission", "apply", "enroll", "enrolment", "register", "registration", "how to apply", "how to register", "application process", "join school"],
            "reply": "ðŸ“‹ **Admission Process at Gumma Public School:**\n\n**Step 1:** Create an account on this portal (/register)\n**Step 2:** Fill the Admission Form with student details (/admission_form)\n**Step 3:** Upload Transfer Certificate (TC) and Photo\n**Step 4:** Pay the â‚¹5,000 registration fee online\n**Step 5:** Wait for document verification (2â€“5 working days)\n**Step 6:** Receive final Approval & offer letter\n\nðŸ“… Admissions for 2026â€“2027 session are **currently open!**\n\nNeed help? Go to `/register` to get started."
        },
        # Eligibility
        {
            "triggers": ["eligible", "eligibility", "criteria", "requirement", "qualify", "qualification", "who can apply", "age"],
            "reply": "âœ… **Admission Eligibility Criteria:**\n\n| Class | Age / Academic Requirement |\n|-------|-----------------------------|\n| Class KG | 3â€“4 years |\n| Class 1 | 5â€“6 years |\n| Class 6 | 10â€“12 years |\n| Class 9 | 13â€“15 years |\n| Class 11 & 12 | Must have passed 10th / 11th board exams |\n\nðŸ“œ **Documents Required:**\nâ€¢ Birth Certificate\nâ€¢ Transfer Certificate (TC) from previous school\nâ€¢ Passport-size photographs\nâ€¢ Previous year marksheet\nâ€¢ Aadhar Card (parent/student)"
        },
        # Grades / classes offered
        {
            "triggers": ["grade", "class", "classes", "stream", "science", "commerce", "arts", "which grade", "what class", "available grades", "medical", "non medical", "non-medical", "11th", "12th", "subjects", "hpbose"],
            "reply": "ðŸ“š **Classes Available at Gumma Public School (Class KG to 12th):**\n\nðŸ‘¶ **Pre-Primary** â€” Kindergarten (Class KG)\nðŸ”µ **Primary** â€” Class 1 to Class 5\nðŸŸ¢ **Middle** â€” Class 6 to Class 8\nðŸŸ¡ **Secondary** â€” Class 9 & Class 10\nðŸ”´ **Senior Secondary** â€” Class 11 & Class 12\n\n**Streams in Class 11 & 12:**\nâ€¢ ðŸŽ¨ **Arts (Humanities)** â€” Elective Subjects:\n  1. History\n  2. Political Science\n  3. Geography\n  4. Sociology\n  5. Psychology\n  6. Public Administration\n  7. Economics\n  8. Sanskrit (Elective)\n  9. Urdu\n  10. Music (Vocal/Instrumental)\n  11. Fine Arts (Painting/Graphics/Sculpture)\n  12. Physical Education / Yoga\n  13. Human Ecology & Family Science (Home Science)\n  14. Computer Science / Mathematics\nâ€¢ ðŸ“Š **Commerce** â€” Accountancy, Business Studies, Economics, Mathematics / Informatics Practices\nâ€¢ ðŸ§ª **Science (Medical)** â€” Physics, Chemistry, Biology + Optional Mathematics / PE / CS\nâ€¢ ðŸ”¬ **Science (Non-Medical)** â€” Physics, Chemistry, Mathematics + Optional CS / PE / Economics\n\nAll senior secondary classes follow HP Board (HPBOSE) curriculum with English as medium of instruction."
        },
        # Fees
        {
            "triggers": ["fee", "fees", "tuition", "cost", "charges", "price", "how much", "payment", "pay", "registration fee", "annual fee"],
            "reply": "ðŸ’° **Fee Structure â€” Gumma Public School:**\n\n| Fee Type | Amount |\n|----------|--------|\n| Admission / Registration Fee | â‚¹5,000 (one-time) |\n| Annual Tuition Fee (Primary) | â‚¹45,000/year |\n| Annual Tuition Fee (Middle) | â‚¹55,000/year |\n| Annual Tuition Fee (Secondary) | â‚¹65,000/year |\n| Senior Secondary (Science) | â‚¹75,000/year |\n| Senior Secondary (Commerce) | â‚¹68,000/year |\n\nðŸ’³ **Payment Options:** Online (Debit/Credit/UPI) via our portal\n\nGo to `/fees` to make your payment."
        },
        # School timing
        {
            "triggers": ["timing", "timings", "time", "hours", "school hours", "schedule", "open", "close", "what time"],
            "reply": "ðŸ• **School Timings â€” Gumma Public School:**\n\nðŸ“… **Monday to Saturday**\nâ€¢ School Opens: **7:45 AM**\nâ€¢ Assembly: **8:00 AM**\nâ€¢ Class Hours: **8:15 AM â€“ 2:15 PM**\nâ€¢ Lunch Break: **12:00 PM â€“ 12:30 PM**\nâ€¢ After-school activities: **2:30 PM â€“ 4:00 PM**\n\nðŸš« **Closed:** Sundays and National Holidays\n\nðŸ“ž Office hours: 9:00 AM â€“ 4:00 PM (Monâ€“Sat)"
        },
        # Facilities
        {
            "triggers": ["facility", "facilities", "lab", "library", "sports", "swimming", "playground", "computer", "science lab", "infrastructure", "hostel", "bus"],
            "reply": "ðŸ« **World-Class Facilities at Gumma Public School:**\n\nðŸ”¬ **Academic:** Fully-equipped Science, Computer, and Language Labs\nðŸ“š **Library:** 15,000+ books, digital reading section, e-resources\nðŸŠ **Sports:** Olympic-size Swimming Pool, Cricket Ground, Basketball & Volleyball Courts\nðŸŽ¨ **Arts & Music:** Dedicated Art Studios, Music Rooms with professional instruments\nðŸŽ **Dining:** Hygienic canteen with nutrition-focused menu\nðŸšŒ **Transport:** School bus network covering 35+ routes across the city\nðŸ  **Hostel:** Separate boys' and girls' hostels with 24/7 supervision"
        },
        # Extracurriculars / clubs
        {
            "triggers": ["club", "clubs", "extracurricular", "activity", "activities", "sports", "chess", "robotics", "dance", "music", "art", "coding"],
            "reply": "ðŸŽ¯ **Extracurricular Activities & Clubs:**\n\nðŸ¤– **STEM Clubs:** Robotics, Coding & AI, Math Olympiad\nðŸŽ¨ **Arts:** Painting, Craft, Photography Club\nðŸŽµ **Performing Arts:** Music (Vocal & Instrumental), Dance, Drama\nâ™Ÿï¸ **Intellectual:** Chess, Debate, Quiz & Elocution\nâš½ **Sports:** Football, Cricket, Badminton, Athletics, Swimming\nðŸŒ± **Eco Club:** Environment awareness, plantation drives\nðŸ“° **Journalism:** School Magazine & Student Council\n\nAll students are encouraged to join at least **two clubs** per semester."
        },
        # Contact info
        {
            "triggers": ["contact", "phone", "email", "address", "location", "where is", "how to reach", "call", "visit", "office"],
            "reply": "ðŸ“ž **Contact Gumma Public School:**\n\nðŸ“ **Address:** Sector-4, Admission Division, Shimla, Himachal Pradesh â€” 171001\n\nðŸ“§ **Email:**\nâ€¢ Admissions: admissions@gummapublicschool.edu\nâ€¢ Principal: principal@gummapublicschool.edu\nâ€¢ Support: support@gummapublicschool.edu\n\nâ˜Žï¸ **Phone:**\nâ€¢ Admissions Helpline: +91 (177) 283-9483\nâ€¢ School Office: +91 (177) 283-9484\n\nðŸ• **Office Hours:** Monâ€“Sat, 9:00 AM â€“ 4:00 PM\n\nOr visit us at `/contact` to send a message."
        },
        # Status / tracking
        {
            "triggers": ["status", "track", "application status", "check status", "where is my application", "approved", "pending", "rejected", "when will i know"],
            "reply": "ðŸ” **Track Your Application Status:**\n\nYou can check your real-time admission status at `/status` after logging in.\n\n**Status meanings:**\nâ€¢ ðŸŸ¡ **Pending Review** â€” Form submitted, awaiting admin review\nâ€¢ ðŸ”µ **Verifying Documents** â€” TC and photo being verified\nâ€¢ âœ… **Approved** â€” Admission granted! Pay fees to confirm seat\nâ€¢ ðŸ”´ **Action Required** â€” Admin has requested corrections\nâ€¢ âŒ **Rejected** â€” Application declined (check admin comments)\n\nâ±ï¸ Typical processing time: **3â€“7 working days**"
        },
        # Results / academics
        {
            "triggers": ["result", "results", "exam", "examination", "board", "cbse", "performance", "marks", "percentage", "pass", "fail"],
            "reply": "ðŸŽ“ **Academic Excellence at Gumma Public School:**\n\nOur students consistently outperform state and national averages!\n\nðŸ“Š **Recent CBSE Board Results (2025):**\nâ€¢ Grade 10 Pass Rate: **99.2%** (School avg: 84.7%)\nâ€¢ Grade 12 Pass Rate: **98.8%** (School avg: 82.3%)\nâ€¢ Students scoring 90%+: **67% of candidates**\nâ€¢ Top scorers sent to IITs, NITs, and top medical colleges\n\nðŸ† Our students have won **National Science Olympiad** and **State-level Debate Championships** in 2025."
        },
        # Principal / teachers
        {
            "triggers": ["principal", "teacher", "staff", "faculty", "management", "who runs", "head"],
            "reply": "ðŸ‘©â€ðŸ’¼ **Our Leadership Team:**\n\nðŸŽ“ **Principal:** Dr. Sunita Verma, M.Ed, PhD (Education)\nâ€¢ 25+ years of experience in educational leadership\nâ€¢ Former Director, State Education Board\n\nðŸ‘¨â€ðŸ« **Faculty Highlights:**\nâ€¢ 120+ qualified and certified teaching staff\nâ€¢ Average experience: 12 years per teacher\nâ€¢ Regular training workshops and professional development\nâ€¢ Dedicated counselors and special educators\n\nFor faculty meetings, contact the school office at +91 (177) 283-9484."
        },
        # Hostel
        {
            "triggers": ["hostel", "boarding", "dormitory", "stay", "accommodation", "residential"],
            "reply": "ðŸ  **Hostel / Boarding Facilities:**\n\n**Gumma Public School offers fully-managed residential boarding:**\n\nâ€¢ Separate wings for Boys and Girls\nâ€¢ 24/7 Security with CCTV surveillance\nâ€¢ Qualified Wardens and Matrons on duty\nâ€¢ Study hours: 6:00 PM â€“ 8:00 PM (supervised)\nâ€¢ Medical room with visiting doctor 3x per week\nâ€¢ Nutritious meals (Breakfast + Lunch + Dinner)\n\nðŸ’° **Hostel Fee:** â‚¹1,20,000/year (includes meals)\n\nContact admissions office for hostel availability and allocation."
        },
        # Transport / bus
        {
            "triggers": ["bus", "transport", "van", "pick up", "drop", "route", "commute", "distance"],
            "reply": "ðŸšŒ **School Transport Network:**\n\nGumma Public School operates **35+ bus routes** covering major areas of Shimla and surrounding regions.\n\nðŸ“ **Key Routes Include:**\nâ€¢ Mall Road â†’ School\nâ€¢ Lakkar Bazaar â†’ School\nâ€¢ Sanjauli â†’ School\nâ€¢ Kasumpti â†’ School\nâ€¢ Dhalli â†’ School\n\nðŸ’° **Transport Fee:** â‚¹18,000â€“â‚¹24,000/year (distance-based)\n\nðŸ“ž For route enquiries and new registration, contact: +91 (177) 283-9483"
        },
        # Documents needed
        {
            "triggers": ["document", "documents", "what do i need", "tc", "transfer certificate", "marksheet", "certificate", "required"],
            "reply": "ðŸ“„ **Documents Required for Admission:**\n\nâœ… **Mandatory:**\nâ€¢ Transfer Certificate (TC) from previous school\nâ€¢ Last year's Report Card / Marksheet\nâ€¢ Birth Certificate (original + photocopy)\nâ€¢ 4 Passport-size Photographs (white background)\nâ€¢ Aadhar Card (student + parent)\nâ€¢ Residence Proof\n\nðŸ“¤ **Upload:** TC and photo can be uploaded directly through the Admission Form at `/admission_form`\n\nâš ï¸ Originals must be submitted in-person on the first day of school."
        },
        # Scholarships
        {
            "triggers": ["scholarship", "discount", "concession", "merit", "free", "bursary", "sibling", "financial aid"],
            "reply": "ðŸ… **Scholarships & Fee Concessions:**\n\nðŸŒŸ **Merit Scholarship:** Students scoring 95%+ in CBSE boards get **25% tuition waiver**\nðŸ‘¨â€ðŸ‘©â€ðŸ‘§ **Sibling Concession:** 2nd sibling gets **15% discount** on tuition\nðŸŽ–ï¸ **Sports Quota:** Outstanding athletes (state/national level) â€” special fee structure\nðŸ¤² **Economic Need:** Limited seats under EWS/BPL category with fee waiver up to 100%\n\nFor scholarship applications, contact: admissions@gummapublicschool.edu"
        },
        # General / thanks
        {
            "triggers": ["thank", "thanks", "thank you", "bye", "goodbye", "ok", "okay", "great", "awesome", "nice"],
            "reply": "ðŸ˜Š You're welcome! We're happy to help.\n\nIf you have any more questions about **Gumma Public School**, feel free to ask anytime! You can also visit our `/contact` page to reach the admissions office directly.\n\nðŸŒŸ *Inspiring Minds, Shaping Futures â€” Gumma Public School*"
        },
    ]

    # Match user message against triggers
    response = None
    for entry in SCHOOL_KB:
        if any(trigger in user_msg for trigger in entry["triggers"]):
            response = entry["reply"]
            break

    # Fallback response
    if not response:
        response = (
            "ðŸ¤” I'm not sure I have specific information about that. "
            "Here's what I **can** help you with:\n\n"
            "â€¢ ðŸ“‹ **Admissions** â€” type 'admission'\n"
            "â€¢ ðŸ’° **Fees** â€” type 'fees'\n"
            "â€¢ ðŸ« **Facilities** â€” type 'facilities'\n"
            "â€¢ ðŸ• **Timings** â€” type 'timing'\n"
            "â€¢ ðŸ“ž **Contact** â€” type 'contact'\n"
            "â€¢ ðŸ“š **Grades offered** â€” type 'grades'\n"
            "â€¢ ðŸ… **Scholarships** â€” type 'scholarship'\n\n"
            "Or visit `/contact` to reach our admissions team directly."
        )

    return jsonify({"reply": response})


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if "user" in session:
        return redirect(url_for("dashboard"))

    message = ""
    step = "username"
    username = ""
    security_question = ""

    if request.method == "POST":
        action = request.form.get("action", "")
        username = request.form.get("username", "").strip()

        if action == "get_question":
            # Step 1: Verify username exists
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            conn.close()

            if user:
                # Use a simple security question (since we don't have security_question in schema)
                security_question = f"What is the username you registered with?"
                step = "reset"
            else:
                message = "Username not found. Please check and try again."
                step = "username"

        elif action == "reset":
            # Step 2: Verify answer and reset password
            security_answer = request.form.get("security_answer", "").strip()
            new_password = request.form.get("new_password", "")
            confirm_new_password = request.form.get("confirm_new_password", "")

            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

            if not user:
                conn.close()
                message = "Username not found."
                step = "username"
            elif security_answer.lower() != username.lower():
                conn.close()
                message = "Security answer is incorrect."
                security_question = f"What is the username you registered with?"
                step = "reset"
            elif not new_password:
                conn.close()
                message = "New password is required."
                security_question = f"What is the username you registered with?"
                step = "reset"
            elif new_password != confirm_new_password:
                conn.close()
                message = "Passwords do not match."
                security_question = f"What is the username you registered with?"
                step = "reset"
            else:
                conn.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
                conn.commit()
                conn.close()
                session.clear()
                flash("Password reset successful! Please login with your new password.")
                return redirect(url_for("login"))

    return render_template("forgot_password.html",
                           message=message,
                           step=step,
                           username=username,
                           security_question=security_question)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True, port=5001)

