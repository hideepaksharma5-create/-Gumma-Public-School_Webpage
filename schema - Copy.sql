-- Database Schema for Gumma Public School Admission Portal

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student', -- 'admin' or 'student'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    student_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    gender TEXT NOT NULL,
    parent_name TEXT NOT NULL,
    parent_email TEXT NOT NULL,
    parent_phone TEXT NOT NULL,
    grade_applying TEXT NOT NULL,
    stream TEXT,
    subjects TEXT,
    previous_school TEXT,
    tc_filename TEXT,
    photo_filename TEXT,
    status TEXT DEFAULT 'Pending Review', -- 'Pending Review', 'Verifying Documents', 'Approved', 'Action Required', 'Rejected'
    comments TEXT,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL DEFAULT 5000.0,
    status TEXT DEFAULT 'Unpaid', -- 'Unpaid', 'Paid'
    transaction_id TEXT,
    payment_date DATETIME,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Seed Administrator User
-- Default credentials: admin / adminlogin[1234]
INSERT OR IGNORE INTO users (id, username, password, role) 
VALUES (1, 'admin', 'adminlogin[1234]', 'admin');
