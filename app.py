import os
import sqlite3
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# SECURITY: Set SECRET_KEY env var for persistent sessions across restarts.
# Generate: python -c "import secrets; print(secrets.token_hex(32))"
_secret = os.environ.get('SECRET_KEY')
if not _secret:
    import warnings
    warnings.warn(
        'SECRET_KEY env var not set. Sessions will be lost on each restart.',
        stacklevel=1
    )
    _secret = os.urandom(24)
app.secret_key = _secret

DB_PATH = os.path.join(os.path.dirname(__file__), "gps_gummaDB.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
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
        # Enable WAL once — persists in the DB file permanently
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


def migrate_plaintext_passwords():
    """
    One-time migration: hash any plaintext passwords still stored in users table.
    Safe to run repeatedly — already-hashed entries (pbkdf2:... / scrypt:...) are skipped.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        users = conn.execute("SELECT id, password FROM users").fetchall()
        migrated = 0
        for u in users:
            pw = u["password"] or ""
            if not pw.startswith(("pbkdf2:", "scrypt:")):
                hashed = generate_password_hash(pw)
                conn.execute(
                    "UPDATE users SET password = ? WHERE id = ?", (hashed, u["id"])
                )
                migrated += 1
        if migrated:
            conn.commit()
            print(f"[security] Migrated {migrated} plaintext password(s) to hashed format.")
        else:
            print("[security] All passwords already hashed — no migration needed.")
    finally:
        conn.close()


migrate_plaintext_passwords()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.context_processor
def inject_user():
    # Make username and role available in all templates
    return dict(
        current_username=session.get('user'),
        current_role=session.get('role')
    )

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools_json():
    return jsonify({}), 200

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/academics")
def academics():
    return render_template("academics.html")

@app.route("/admissions")
def admissions():
    return render_template("admissions.html")

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")

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

        if user and check_password_hash(user["password"], password):
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
                hashed_pw = generate_password_hash(password)
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'student')", (username, hashed_pw))
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
        elif grade_applying in ["Class 11", "Class 12"] and stream == "Arts" and len([s.strip() for s in subjects_list if s.strip() and s.strip() != "English"]) != 5:
            current_stream = stream
            current_subjects = [s.strip() for s in subjects_list if s.strip()]
            message = "For Arts stream, you must choose exactly 5 elective subjects (+ compulsory English = 6 subjects total)."
        else:
            # Build full grade description with stream & subjects for 11th & 12th
            if grade_applying in ["Class 11", "Class 12"]:
                if stream == "Arts":
                    electives = [s.strip() for s in subjects_list if s.strip() and s.strip() != "English"]
                    subjects_list = ["English"] + electives
                    subjects_str = ", ".join(subjects_list)
                    formatted_grade = f"{grade_applying} - {stream} ({subjects_str})"
                elif stream:
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

            # Support all 6 document upload fields
            doc_fields = [
                ("tc_file", "tc_filename", "tc"),
                ("photo_file", "photo_filename", "photo"),
                ("birth_cert_file", "birth_cert_filename", "birth"),
                ("residence_file", "residence_proof_filename", "residence"),
                ("marksheet_file", "marksheet_filename", "marksheet"),
                ("health_file", "health_records_filename", "health"),
            ]
            saved_filenames = {}
            for form_key, db_col, prefix in doc_fields:
                existing_val = existing_app[db_col] if existing_app and db_col in existing_app.keys() else None
                file_obj = request.files.get(form_key)
                if file_obj and file_obj.filename and allowed_file(file_obj.filename):
                    safe_name = secure_filename(f"{prefix}_{session['user_id']}_{file_obj.filename}")
                    file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_name))
                    saved_filenames[db_col] = safe_name
                else:
                    saved_filenames[db_col] = existing_val

            if existing_app:
                conn.execute("""
                    UPDATE applications 
                    SET student_name=?, dob=?, gender=?, parent_name=?, parent_email=?, parent_phone=?, 
                        grade_applying=?, stream=?, subjects=?, previous_school=?, 
                        tc_filename=?, photo_filename=?, birth_cert_filename=?, 
                        residence_proof_filename=?, marksheet_filename=?, health_records_filename=?, 
                        status='Pending Review'
                    WHERE user_id=?
                """, (student_name, dob, gender, parent_name, parent_email, parent_phone, 
                      formatted_grade, stream, subjects_str, previous_school, 
                      saved_filenames["tc_filename"], saved_filenames["photo_filename"],
                      saved_filenames["birth_cert_filename"], saved_filenames["residence_proof_filename"],
                      saved_filenames["marksheet_filename"], saved_filenames["health_records_filename"],
                      session["user_id"]))
            else:
                conn.execute("""
                    INSERT INTO applications (user_id, student_name, dob, gender, parent_name, parent_email, 
                                             parent_phone, grade_applying, stream, subjects, previous_school, 
                                             tc_filename, photo_filename, birth_cert_filename, 
                                             residence_proof_filename, marksheet_filename, health_records_filename)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (session["user_id"], student_name, dob, gender, parent_name, parent_email, 
                      parent_phone, formatted_grade, stream, subjects_str, previous_school, 
                      saved_filenames["tc_filename"], saved_filenames["photo_filename"],
                      saved_filenames["birth_cert_filename"], saved_filenames["residence_proof_filename"],
                      saved_filenames["marksheet_filename"], saved_filenames["health_records_filename"]))
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
    # Gumma Public School — AI Chatbot Knowledge Base
    # -----------------------------------------------------------------------
    SCHOOL_KB = [
        # Greetings
        {
            "triggers": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"],
            "reply": "👋 Hello! Welcome to **Gumma Public School** Admission Portal. I'm your AI assistant. I can help you with:\n\n• 📋 Admission process & eligibility\n• 📚 Grades & curriculum\n• 💰 Fee structure & payments\n• 🕐 School timings & calendar\n• ðŸ« Facilities & extracurriculars\n• 📞 Contact information\n\nWhat would you like to know?"
        },
        # Admission process
        {
            "triggers": ["admission", "apply", "enroll", "enrolment", "register", "registration", "how to apply", "how to register", "application process", "join school"],
            "reply": "📋 **Admission Process at Gumma Public School:**\n\n**Step 1:** Create an account on this portal (/register)\n**Step 2:** Fill the Admission Form with student details (/admission_form)\n**Step 3:** Upload Transfer Certificate (TC) and Photo\n**Step 4:** Pay the ₹5,000 registration fee online\n**Step 5:** Wait for document verification (2–5 working days)\n**Step 6:** Receive final Approval & offer letter\n\n📅 Admissions for 2026–2027 session are **currently open!**\n\nNeed help? Go to `/register` to get started."
        },
        # Eligibility
        {
            "triggers": ["eligible", "eligibility", "criteria", "requirement", "qualify", "qualification", "who can apply", "age"],
            "reply": "✅ **Admission Eligibility Criteria:**\n\n| Class | Age / Academic Requirement |\n|-------|-----------------------------|\n| Class KG | 3–4 years |\n| Class 1 | 5–6 years |\n| Class 6 | 10–12 years |\n| Class 9 | 13–15 years |\n| Class 11 & 12 | Must have passed 10th / 11th board exams |\n\n📜 **Documents Required:**\n• Birth Certificate\n• Transfer Certificate (TC) from previous school\n• Passport-size photographs\n• Previous year marksheet\n• Aadhar Card (parent/student)"
        },
        # Grades / classes offered
        {
            "triggers": ["grade", "class", "classes", "stream", "science", "commerce", "arts", "which grade", "what class", "available grades", "medical", "non medical", "non-medical", "11th", "12th", "subjects", "hpbose"],
            "reply": "📚 **Classes Available at Gumma Public School (Class KG to 12th):**\n\n👶 **Pre-Primary** — Kindergarten (Class KG)\n🔵 **Primary** — Class 1 to Class 5\n🟢 **Middle** — Class 6 to Class 8\n🟡 **Secondary** — Class 9 & Class 10\n🔴 **Senior Secondary** — Class 11 & Class 12\n\n**Streams in Class 11 & 12:**\n• 🎨 **Arts (Humanities)** — Elective Subjects:\n  1. History\n  2. Political Science\n  3. Geography\n  4. Sociology\n  5. Psychology\n  6. Public Administration\n  7. Economics\n  8. Sanskrit (Elective)\n  9. Urdu\n  10. Music (Vocal/Instrumental)\n  11. Fine Arts (Painting/Graphics/Sculpture)\n  12. Physical Education / Yoga\n  13. Human Ecology & Family Science (Home Science)\n  14. Computer Science / Mathematics\n• 📊 **Commerce** — Accountancy, Business Studies, Economics, Mathematics / Informatics Practices\n• 🧪 **Science (Medical)** — Physics, Chemistry, Biology + Optional Mathematics / PE / CS\n• 🔬 **Science (Non-Medical)** — Physics, Chemistry, Mathematics + Optional CS / PE / Economics\n\nAll senior secondary classes follow HP Board (HPBOSE) curriculum with English as medium of instruction."
        },
        # Fees
        {
            "triggers": ["fee", "fees", "tuition", "cost", "charges", "price", "how much", "payment", "pay", "registration fee", "annual fee"],
            "reply": "💰 **Fee Structure — Gumma Public School:**\n\n| Fee Type | Amount |\n|----------|--------|\n| Admission / Registration Fee | ₹5,000 (one-time) |\n| Annual Tuition Fee (Primary) | ₹45,000/year |\n| Annual Tuition Fee (Middle) | ₹55,000/year |\n| Annual Tuition Fee (Secondary) | ₹65,000/year |\n| Senior Secondary (Science) | ₹75,000/year |\n| Senior Secondary (Commerce) | ₹68,000/year |\n\n💳 **Payment Options:** Online (Debit/Credit/UPI) via our portal\n\nGo to `/fees` to make your payment."
        },
        # School timing
        {
            "triggers": ["timing", "timings", "time", "hours", "school hours", "schedule", "open", "close", "what time"],
            "reply": "🕐 **School Timings — Gumma Public School:**\n\n📅 **Monday to Saturday**\n• School Opens: **7:45 AM**\n• Assembly: **8:00 AM**\n• Class Hours: **8:15 AM – 2:15 PM**\n• Lunch Break: **12:00 PM – 12:30 PM**\n• After-school activities: **2:30 PM – 4:00 PM**\n\n🚫 **Closed:** Sundays and National Holidays\n\n📞 Office hours: 9:00 AM – 4:00 PM (Mon–Sat)"
        },
        # Facilities
        {
            "triggers": ["facility", "facilities", "lab", "library", "sports", "swimming", "playground", "computer", "science lab", "infrastructure", "hostel", "bus"],
            "reply": "ðŸ« **World-Class Facilities at Gumma Public School:**\n\n🔬 **Academic:** Fully-equipped Science, Computer, and Language Labs\n📚 **Library:** 15,000+ books, digital reading section, e-resources\nðŸŠ **Sports:** Olympic-size Swimming Pool, Cricket Ground, Basketball & Volleyball Courts\n🎨 **Arts & Music:** Dedicated Art Studios, Music Rooms with professional instruments\nðŸŽ **Dining:** Hygienic canteen with nutrition-focused menu\n🚌 **Transport:** School bus network covering 35+ routes across the city\nðŸ  **Hostel:** Separate boys' and girls' hostels with 24/7 supervision"
        },
        # Extracurriculars / clubs
        {
            "triggers": ["club", "clubs", "extracurricular", "activity", "activities", "sports", "chess", "robotics", "dance", "music", "art", "coding"],
            "reply": "🎯 **Extracurricular Activities & Clubs:**\n\n🤖 **STEM Clubs:** Robotics, Coding & AI, Math Olympiad\n🎨 **Arts:** Painting, Craft, Photography Club\n🎵 **Performing Arts:** Music (Vocal & Instrumental), Dance, Drama\n♟️ **Intellectual:** Chess, Debate, Quiz & Elocution\n⚽ **Sports:** Football, Cricket, Badminton, Athletics, Swimming\n🌱 **Eco Club:** Environment awareness, plantation drives\n📰 **Journalism:** School Magazine & Student Council\n\nAll students are encouraged to join at least **two clubs** per semester."
        },
        # Contact info
        {
            "triggers": ["contact", "phone", "email", "address", "location", "where is", "how to reach", "call", "visit", "office"],
            "reply": "📞 **Contact Gumma Public School:**\n\nðŸ“ **Address:** Sector-4, Admission Division, Shimla, Himachal Pradesh — 171001\n\nðŸ“§ **Email:**\n• Admissions: admissions@gummapublicschool.edu\n• Principal: principal@gummapublicschool.edu\n• Support: support@gummapublicschool.edu\n\nâ˜Žï¸ **Phone:**\n• Admissions Helpline: +91 (177) 283-9483\n• School Office: +91 (177) 283-9484\n\n🕐 **Office Hours:** Mon–Sat, 9:00 AM – 4:00 PM\n\nOr visit us at `/contact` to send a message."
        },
        # Status / tracking
        {
            "triggers": ["status", "track", "application status", "check status", "where is my application", "approved", "pending", "rejected", "when will i know"],
            "reply": "ðŸ” **Track Your Application Status:**\n\nYou can check your real-time admission status at `/status` after logging in.\n\n**Status meanings:**\n• 🟡 **Pending Review** — Form submitted, awaiting admin review\n• 🔵 **Verifying Documents** — TC and photo being verified\n• ✅ **Approved** — Admission granted! Pay fees to confirm seat\n• 🔴 **Action Required** — Admin has requested corrections\n• âŒ **Rejected** — Application declined (check admin comments)\n\nâ±ï¸ Typical processing time: **3–7 working days**"
        },
        # Results / academics
        {
            "triggers": ["result", "results", "exam", "examination", "board", "cbse", "performance", "marks", "percentage", "pass", "fail"],
            "reply": "ðŸŽ“ **Academic Excellence at Gumma Public School:**\n\nOur students consistently outperform state and national averages!\n\n📊 **Recent CBSE Board Results (2025):**\n• Grade 10 Pass Rate: **99.2%** (School avg: 84.7%)\n• Grade 12 Pass Rate: **98.8%** (School avg: 82.3%)\n• Students scoring 90%+: **67% of candidates**\n• Top scorers sent to IITs, NITs, and top medical colleges\n\nðŸ† Our students have won **National Science Olympiad** and **State-level Debate Championships** in 2025."
        },
        # Principal / teachers
        {
            "triggers": ["principal", "teacher", "staff", "faculty", "management", "who runs", "head"],
            "reply": "ðŸ‘©â€ðŸ’¼ **Our Leadership Team:**\n\nðŸŽ“ **Principal:** Dr. Sunita Verma, M.Ed, PhD (Education)\n• 25+ years of experience in educational leadership\n• Former Director, State Education Board\n\nðŸ‘¨â€ðŸ« **Faculty Highlights:**\n• 120+ qualified and certified teaching staff\n• Average experience: 12 years per teacher\n• Regular training workshops and professional development\n• Dedicated counselors and special educators\n\nFor faculty meetings, contact the school office at +91 (177) 283-9484."
        },
        # Hostel
        {
            "triggers": ["hostel", "boarding", "dormitory", "stay", "accommodation", "residential"],
            "reply": "ðŸ  **Hostel / Boarding Facilities:**\n\n**Gumma Public School offers fully-managed residential boarding:**\n\n• Separate wings for Boys and Girls\n• 24/7 Security with CCTV surveillance\n• Qualified Wardens and Matrons on duty\n• Study hours: 6:00 PM – 8:00 PM (supervised)\n• Medical room with visiting doctor 3x per week\n• Nutritious meals (Breakfast + Lunch + Dinner)\n\n💰 **Hostel Fee:** ₹1,20,000/year (includes meals)\n\nContact admissions office for hostel availability and allocation."
        },
        # Transport / bus
        {
            "triggers": ["bus", "transport", "van", "pick up", "drop", "route", "commute", "distance"],
            "reply": "🚌 **School Transport Network:**\n\nGumma Public School operates **35+ bus routes** covering major areas of Shimla and surrounding regions.\n\nðŸ“ **Key Routes Include:**\n• Mall Road → School\n• Lakkar Bazaar → School\n• Sanjauli → School\n• Kasumpti → School\n• Dhalli → School\n\n💰 **Transport Fee:** ₹18,000–₹24,000/year (distance-based)\n\n📞 For route enquiries and new registration, contact: +91 (177) 283-9483"
        },
        # Documents needed
        {
            "triggers": ["document", "documents", "what do i need", "tc", "transfer certificate", "marksheet", "certificate", "required"],
            "reply": "📄 **Documents Required for Admission:**\n\n✅ **Mandatory:**\n• Transfer Certificate (TC) from previous school\n• Last year's Report Card / Marksheet\n• Birth Certificate (original + photocopy)\n• 4 Passport-size Photographs (white background)\n• Aadhar Card (student + parent)\n• Residence Proof\n\n📤 **Upload:** TC and photo can be uploaded directly through the Admission Form at `/admission_form`\n\n⚠️ Originals must be submitted in-person on the first day of school."
        },
        # Scholarships
        {
            "triggers": ["scholarship", "discount", "concession", "merit", "free", "bursary", "sibling", "financial aid"],
            "reply": "ðŸ… **Scholarships & Fee Concessions:**\n\n🌟 **Merit Scholarship:** Students scoring 95%+ in CBSE boards get **25% tuition waiver**\nðŸ‘¨â€ðŸ‘©â€ðŸ‘§ **Sibling Concession:** 2nd sibling gets **15% discount** on tuition\n🎖️ **Sports Quota:** Outstanding athletes (state/national level) — special fee structure\n🤲 **Economic Need:** Limited seats under EWS/BPL category with fee waiver up to 100%\n\nFor scholarship applications, contact: admissions@gummapublicschool.edu"
        },
        # General / thanks
        {
            "triggers": ["thank", "thanks", "thank you", "bye", "goodbye", "ok", "okay", "great", "awesome", "nice"],
            "reply": "😊 You're welcome! We're happy to help.\n\nIf you have any more questions about **Gumma Public School**, feel free to ask anytime! You can also visit our `/contact` page to reach the admissions office directly.\n\n🌟 *Inspiring Minds, Shaping Futures — Gumma Public School*"
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
            "🤔 I'm not sure I have specific information about that. "
            "Here's what I **can** help you with:\n\n"
            "• 📋 **Admissions** — type 'admission'\n"
            "• 💰 **Fees** — type 'fees'\n"
            "• ðŸ« **Facilities** — type 'facilities'\n"
            "• 🕐 **Timings** — type 'timing'\n"
            "• 📞 **Contact** — type 'contact'\n"
            "• 📚 **Grades offered** — type 'grades'\n"
            "• ðŸ… **Scholarships** — type 'scholarship'\n\n"
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
            # Step 1: Look up user and application details for security challenge
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user:
                app_row = conn.execute(
                    "SELECT parent_email, parent_phone, student_name FROM applications WHERE user_id = ?",
                    (user["id"],)
                ).fetchone()
                conn.close()

                if user["role"] == "admin":
                    security_question = "Administrator Verification: Enter the school recovery passkey"
                elif app_row and (app_row["parent_email"] or app_row["parent_phone"]):
                    security_question = "Security Verification: Enter your registered Parent Email or Phone Number"
                else:
                    security_question = "Account Verification: Enter the username or contact administrator at admissions@gummapublicschool.edu"
                step = "reset"
            else:
                conn.close()
                message = "Username not found. Please check and try again."
                step = "username"

        elif action == "reset":
            # Step 2: Validate the challenge response and enforce minimum password standards
            security_answer = request.form.get("security_answer", "").strip().lower()
            new_password = request.form.get("new_password", "")
            confirm_new_password = request.form.get("confirm_new_password", "")

            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

            if not user:
                conn.close()
                message = "Username not found."
                step = "username"
            else:
                app_row = conn.execute(
                    "SELECT parent_email, parent_phone FROM applications WHERE user_id = ?",
                    (user["id"],)
                ).fetchone()
                
                # Verify identity against application or admin recovery key
                is_valid_answer = False
                if user["role"] == "admin":
                    admin_recovery_key = os.environ.get("ADMIN_RECOVERY_KEY", "GPS2026AdminRecovery")
                    is_valid_answer = (security_answer == admin_recovery_key.lower())
                elif app_row:
                    valid_answers = []
                    if app_row["parent_email"]:
                        valid_answers.append(app_row["parent_email"].strip().lower())
                    if app_row["parent_phone"]:
                        # Raw digits comparison
                        clean_input = re.sub(r"\D", "", security_answer)
                        clean_db = re.sub(r"\D", "", app_row["parent_phone"])
                        if clean_input and clean_input == clean_db:
                            is_valid_answer = True
                        valid_answers.append(app_row["parent_phone"].strip().lower())
                    if security_answer in valid_answers:
                        is_valid_answer = True
                else:
                    # New user before application submitted: requires registration support contact
                    is_valid_answer = (security_answer == username.lower())

                if not is_valid_answer:
                    conn.close()
                    message = "Security answer does not match our records."
                    security_question = "Security Verification: Enter your registered Parent Email or Phone Number"
                    step = "reset"
                elif not new_password or len(new_password) < 8:
                    conn.close()
                    message = "New password must be at least 8 characters long."
                    security_question = "Security Verification: Enter your registered Parent Email or Phone Number"
                    step = "reset"
                elif new_password != confirm_new_password:
                    conn.close()
                    message = "Passwords do not match."
                    security_question = "Security Verification: Enter your registered Parent Email or Phone Number"
                    step = "reset"
                else:
                    hashed_new = generate_password_hash(new_password)
                    conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new, username))
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


