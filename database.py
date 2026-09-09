import sqlite3

DATABASE = "schoolfix.db"


# -----------------------------
# CREATE DATABASE
# -----------------------------

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    # Admin applications
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            date TEXT
        )
    """)

    # Complaints / Reports
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            category TEXT,
            location TEXT,
            message TEXT,
            status TEXT DEFAULT 'Pending',
            date TEXT,
            admin_note TEXT
        )
    """)

    # Create the two built-in Main Admin accounts
    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role, active)
        VALUES (?, ?, ?, ?)
    """, ("mainadmin1", "ChangeMe123", "main_admin", 1))

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (username, password, role, active)
        VALUES (?, ?, ?, ?)
    """, ("mainadmin2", "ChangeMe456", "main_admin", 1))

    conn.commit()
    conn.close()


# -----------------------------
# USERS
# -----------------------------

def save_user(username, password, role="student"):
    # Public registration can create ONLY students
    if role != "student":
        return False

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (username, password, role, active)
            VALUES (?, ?, ?, 1)
        """, (username, password, "student"))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def get_user(username, password):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM users
        WHERE username = ?
        AND password = ?
        AND active = 1
    """, (username, password))

    user = cursor.fetchone()

    conn.close()

    return user


# -----------------------------
# ADMIN APPLICATIONS
# -----------------------------

def apply_for_admin(username, reason, date):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check that user exists and is a student
    cursor.execute("""
        SELECT role FROM users
        WHERE username = ? AND active = 1
    """, (username,))

    user = cursor.fetchone()

    if not user or user[0] != "student":
        conn.close()
        return False

    # Check if there is already a pending application
    cursor.execute("""
        SELECT id FROM admin_applications
        WHERE username = ? AND status = 'Pending'
    """, (username,))

    existing = cursor.fetchone()

    if existing:
        conn.close()
        return False

    cursor.execute("""
        INSERT INTO admin_applications
        (username, reason, status, date)
        VALUES (?, ?, 'Pending', ?)
    """, (username, reason, date))

    conn.commit()
    conn.close()

    return True


def get_admin_applications():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM admin_applications
        ORDER BY id DESC
    """)

    applications = cursor.fetchall()

    conn.close()

    return applications


def approve_admin(application_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Find applicant
    cursor.execute("""
        SELECT username FROM admin_applications
        WHERE id = ? AND status = 'Pending'
    """, (application_id,))

    application = cursor.fetchone()

    if not application:
        conn.close()
        return False

    username = application[0]

    # Change student into normal admin
    cursor.execute("""
        UPDATE users
        SET role = 'admin'
        WHERE username = ?
        AND role = 'student'
        AND active = 1
    """, (username,))

    # Mark application approved
    cursor.execute("""
        UPDATE admin_applications
        SET status = 'Approved'
        WHERE id = ?
    """, (application_id,))

    conn.commit()
    conn.close()

    return True


def reject_admin(application_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE admin_applications
        SET status = 'Rejected'
        WHERE id = ?
        AND status = 'Pending'
    """, (application_id,))

    conn.commit()

    changed = cursor.rowcount > 0

    conn.close()

    return changed


# -----------------------------
# COMPLAINTS / REPORTS
# -----------------------------

def save_report(username, category, location, message, date):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reports
        (username, category, location, message, status, date, admin_note)
        VALUES (?, ?, ?, ?, 'Pending', ?, '')
    """, (username, category, location, message, date))

    conn.commit()
    conn.close()


def get_all_reports():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM reports
        ORDER BY id DESC
    """)

    reports = cursor.fetchall()

    conn.close()

    return reports


def get_user_reports(username):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM reports
        WHERE username = ?
        ORDER BY id DESC
    """, (username,))

    reports = cursor.fetchall()

    conn.close()

    return reports


def update_report_status(report_id, status, admin_note=""):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE reports
        SET status = ?, admin_note = ?
        WHERE id = ?
    """, (status, admin_note, report_id))

    conn.commit()
    conn.close()


def mark_unreasonable(report_id, admin_note=""):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE reports
        SET status = 'Unreasonable',
            admin_note = ?
        WHERE id = ?
    """, (admin_note, report_id))

    conn.commit()
    conn.close()


def get_unreasonable_reports():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM reports
        WHERE status = 'Unreasonable'
        ORDER BY id DESC
    """)

    reports = cursor.fetchall()

    conn.close()

    return reports


def delete_report(report_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM reports
        WHERE id = ?
    """, (report_id,))

    conn.commit()
    conn.close()