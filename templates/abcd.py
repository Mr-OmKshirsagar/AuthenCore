from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
DATABASE = "database.db"


# ---------------- DATABASE ---------------- #
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('user','admin')) NOT NULL
        )
        """)

        # Certificates Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            cert_id TEXT PRIMARY KEY,
            roll_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            grade TEXT NOT NULL
        )
        """)

        db.commit()


# ---------------- ROUTES ---------------- #

@app.route("/")
def home():
    return render_template("home.html")


# ---------- Signup/Login ---------- #
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       (username, password, role))
            db.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return "Username already exists!"
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?",
                          (username, password)).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
        return "Invalid credentials!"
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- Dashboards ---------- #
@app.route("/user/dashboard")
def user_dashboard():
    if session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user_dashboard.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")


# ---------- Verification ---------- #
@app.route("/admin_verify", methods=["GET"])
def admin_verify():
    return render_template("admin_verify.html")

@app.route("/admin_verify", methods=["POST"])
def verify_manual():
    cert_id = request.form["cert_id"]
    roll_no = request.form["roll_no"]

    db = get_db()
    cert = db.execute("SELECT * FROM certificates WHERE cert_id=? AND roll_no=?",
                      (cert_id, roll_no)).fetchone()

    if cert:
        if session.get("role") == "admin":
            return render_template("admin_verified.html", cert=cert)
        return render_template("user_verified.html", cert=cert)
    else:
        if session.get("role") == "admin":
            return render_template("admin_fake.html")
        return render_template("user_fake.html")
    


import cv2
import numpy as np
from werkzeug.utils import secure_filename

@app.route("/verify_scan", methods=["POST"])
def verify_scan():
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    # Save uploaded file temporarily
    filename = secure_filename(file.filename)
    filepath = os.path.join("uploads", filename)
    os.makedirs("uploads", exist_ok=True)
    file.save(filepath)

    # Read image using OpenCV
    img = cv2.imread(filepath)
    if img is None:
        return "Could not read image", 400

    # Initialize QR detector
    detector = cv2.QRCodeDetector()

    # Detect and decode
    data, bbox, _ = detector.detectAndDecode(img)

    if not data:
        return "No QR code detected", 400

    # Expected QR data format: "cert_id|roll_no"
    try:
        cert_id, roll_no = data.split("|")
    except ValueError:
        return "Invalid QR format", 400

    # Check in database
    db = get_db()
    cert = db.execute(
        "SELECT * FROM certificates WHERE cert_id=? AND roll_no=?",
        (cert_id, roll_no)
    ).fetchone()

    if cert:
        if session.get("role") == "admin":
            return render_template("admin_verified.html", cert=cert)
        return render_template("user_verified.html", cert=cert)
    else:
        if session.get("role") == "admin":
            return render_template("admin_fake.html")
        return render_template("user_fake.html")



# ---------- Certificate Issue (Admin only) ---------- #
@app.route("/admin_issue", methods=["GET", "POST"], endpoint="admin_issue")
def issue_certificate():
    if request.method == "POST":
        cert_id = request.form["cert_id"]
        roll_no = request.form["roll_no"]
        student_name = request.form["student_name"]
        course = request.form["course"]
        year = request.form["year"]
        grade = request.form["grade"]

        db = get_db()
        db.execute(
            "INSERT INTO certificates (cert_id, roll_no, student_name, course, year, grade) VALUES (?, ?, ?, ?, ?, ?)",
            (cert_id, roll_no, student_name, course, year, grade),
        )
        db.commit()

        return f"✅ Certificate {cert_id} issued successfully for {student_name}!"

    return render_template("admin_issue.html")




# ---------- Profile ---------- #
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return render_template("profile.html", user=user)


# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    else:
        init_db()  # ensures missing tables are added
    app.run(debug=True)
