from flask import Flask, request, redirect, session, render_template

from database import (
    init_db,
    save_user,
    get_user,
    apply_for_admin,
    get_admin_applications,
    approve_admin,
    reject_admin,
    save_report,
    get_all_reports,
    get_user_reports,
    update_report_status,
    mark_unreasonable,
    get_unreasonable_reports,
    delete_report
)

from datetime import datetime


app = Flask(__name__)

# Required for Flask sessions
app.secret_key = "schoolfix-secret-key"

# Create database and tables
init_db()


# -----------------------------
# HOME
# -----------------------------

@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# LOGIN
# -----------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # Optional Student/Admin selection from frontend
        login_type = request.form.get("login_type", "").lower()

        # Get REAL user information from database
        user = get_user(username, password)

        if not user:
            return render_template(
                "login.html",
                error="Invalid username or password"
            )

        # Database decides the actual role
        real_role = user[3]

        # If user selected Student
        if login_type == "student":

            if real_role != "student":
                return render_template(
                    "login.html",
                    error="This account is not a Student account."
                )

        # If user selected Admin
        elif login_type == "admin":

            if real_role not in ["admin", "main_admin"]:
                return render_template(
                    "login.html",
                    error="This account is not an Admin account."
                )

        # Store verified information in session
        session["username"] = user[1]
        session["role"] = real_role

        return redirect("/dashboard")

    return render_template("login.html")


# -----------------------------
# LOGOUT
# -----------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# -----------------------------
# DASHBOARD
# -----------------------------

@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    role = session["role"]

    return render_template(
        "dashboard.html",
        username=username,
        role=role
    )


# -----------------------------
# STUDENT REGISTRATION
# -----------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # IMPORTANT:
        # We do NOT take role from the user.
        # Every new account starts as Student.

        success = save_user(
            username,
            password,
            "student"
        )

        if success:
            return redirect("/login")

        return render_template(
            "register.html",
            error="Username already exists."
        )

    return render_template("register.html")


# -----------------------------
# APPLY FOR ADMIN
# -----------------------------

@app.route("/apply-admin", methods=["GET", "POST"])
def apply_admin():

    # Must be logged in
    if "username" not in session:
        return redirect("/login")

    # Only Students can apply
    if session["role"] != "student":
        return "Only students can apply to become Admin."

    if request.method == "POST":

        reason = request.form["reason"]

        date = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        success = apply_for_admin(
            session["username"],
            reason,
            date
        )

        if success:
            return "Admin application submitted successfully!"

        return "You already have a pending application."

    return render_template("apply_admin.html")


# =====================================================
# MAIN ADMIN SECTION
# =====================================================


def main_admin_only():

    return (
        "username" in session
        and session["role"] == "main_admin"
    )


# -----------------------------
# VIEW ADMIN APPLICATIONS
# -----------------------------

@app.route("/admin-applications")
def admin_applications():

    if not main_admin_only():
        return "Access Denied: Main Admin only."

    applications = get_admin_applications()

    return render_template(
        "admin_applications.html",
        applications=applications
    )


# -----------------------------
# APPROVE ADMIN
# -----------------------------

@app.route(
    "/approve-admin/<int:application_id>",
    methods=["POST"]
)
def approve_admin_application(application_id):

    if not main_admin_only():
        return "Access Denied: Main Admin only."

    success = approve_admin(application_id)

    if success:
        return redirect("/admin-applications")

    return "Unable to approve this application."


# -----------------------------
# REJECT ADMIN
# -----------------------------

@app.route(
    "/reject-admin/<int:application_id>",
    methods=["POST"]
)
def reject_admin_application(application_id):

    if not main_admin_only():
        return "Access Denied: Main Admin only."

    success = reject_admin(application_id)

    if success:
        return redirect("/admin-applications")

    return "Unable to reject this application."


# =====================================================
# COMPLAINT SECTION
# =====================================================


# -----------------------------
# SUBMIT COMPLAINT
# -----------------------------

@app.route("/submit-report", methods=["POST"])
def submit_report():

    if "username" not in session:
        return redirect("/login")

    category = request.form["category"]
    location = request.form["location"]
    message = request.form["message"]

    date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    save_report(
        session["username"],
        category,
        location,
        message,
        date
    )

    return redirect("/my-reports")


# -----------------------------
# STUDENT'S REPORTS
# -----------------------------

@app.route("/my-reports")
def my_reports():

    if "username" not in session:
        return redirect("/login")

    reports = get_user_reports(
        session["username"]
    )

    return render_template(
        "my_reports.html",
        reports=reports
    )


# -----------------------------
# ADMIN VIEW ALL REPORTS
# -----------------------------

@app.route("/reports")
def reports():

    if "username" not in session:
        return redirect("/login")

    if session["role"] not in [
        "admin",
        "main_admin"
    ]:
        return "Access Denied."

    reports = get_all_reports()

    return render_template(
        "reports.html",
        reports=reports
    )


# -----------------------------
# UPDATE COMPLAINT STATUS
# -----------------------------

@app.route(
    "/update-report/<int:report_id>",
    methods=["POST"]
)
def update_report(report_id):

    if "username" not in session:
        return redirect("/login")

    if session["role"] not in [
        "admin",
        "main_admin"
    ]:
        return "Access Denied."

    status = request.form["status"]
    admin_note = request.form.get(
        "admin_note",
        ""
    )

    allowed_statuses = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:
        return "Invalid status."

    update_report_status(
        report_id,
        status,
        admin_note
    )

    return redirect("/reports")


# -----------------------------
# MARK COMPLAINT UNREASONABLE
# -----------------------------

@app.route(
    "/unreasonable/<int:report_id>",
    methods=["POST"]
)
def unreasonable(report_id):

    if "username" not in session:
        return redirect("/login")

    if session["role"] not in [
        "admin",
        "main_admin"
    ]:
        return "Access Denied."

    admin_note = request.form.get(
        "admin_note",
        ""
    )

    mark_unreasonable(
        report_id,
        admin_note
    )

    return redirect("/reports")


# -----------------------------
# MAIN ADMIN:
# UNREASONABLE COMPLAINTS
# -----------------------------

@app.route("/unreasonable-reports")
def unreasonable_reports():

    if not main_admin_only():
        return "Access Denied: Main Admin only."

    reports = get_unreasonable_reports()

    return render_template(
        "unreasonable_reports.html",
        reports=reports
    )


# -----------------------------
# DELETE REPORT
# -----------------------------

@app.route(
    "/delete-report/<int:report_id>",
    methods=["POST"]
)
def remove_report(report_id):

    if not main_admin_only():
        return "Access Denied: Main Admin only."

    delete_report(report_id)

    return redirect("/reports")


# -----------------------------
# RUN APPLICATION
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)