"""
Online Conference Registration System
Flask Backend — 4 Pillars of OOP + Admin Dashboard
Database: MySQL (connects to MySQL Workbench via XAMPP)

  1. ABSTRACTION   — BaseModel defines the interface all models must follow
  2. ENCAPSULATION — Database & AdminAuth wrap logic behind clean methods
  3. INHERITANCE   — RegistrationModel inherits from BaseModel
  4. POLYMORPHISM  — to_dict() and validate() behave differently per subclass
"""

from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, flash
)
from abc import ABC, abstractmethod
from datetime import datetime
from functools import wraps
import mysql.connector


# ─────────────────────────────────────────────────────────────
#  MYSQL CONNECTION SETTINGS
#  Make sure XAMPP MySQL is running before starting the app.
#  Change these settings if your MySQL setup is different.
# ─────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",   # XAMPP MySQL host
    "user":     "root",        # default XAMPP MySQL username
    "password": "",            # default XAMPP MySQL password (blank)
    "database": "ocrs_db",     # the database name we will create
}


# ─────────────────────────────────────────────────────────────
#  PILLAR 1 & 2 — ABSTRACTION + ENCAPSULATION
#  Database class hides all MySQL logic inside.
#  Other parts of the code never touch MySQL directly.
# ─────────────────────────────────────────────────────────────
class Database:

    def __init__(self, config: dict):
        # Store connection config privately
        self.__config = config
        self.__setup_database()

    def __connect(self):
        # Open and return a MySQL connection
        return mysql.connector.connect(**self.__config)

    def __setup_database(self):
        # First connect WITHOUT specifying the database
        # so we can create it if it doesn't exist yet
        config_no_db = {k: v for k, v in self.__config.items() if k != "database"}
        conn = mysql.connector.connect(**config_no_db)
        cursor = conn.cursor()

        # Create the database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.__config['database']}")
        cursor.execute(f"USE {self.__config['database']}")

        # Create the registrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id               INT AUTO_INCREMENT PRIMARY KEY,
                entry_no         VARCHAR(20) UNIQUE NOT NULL,
                full_name        VARCHAR(150) NOT NULL,
                student_id       VARCHAR(50) NOT NULL,
                email            VARCHAR(150) NOT NULL,
                department       VARCHAR(100) NOT NULL,
                year_level       VARCHAR(50) NOT NULL,
                role             VARCHAR(50) NOT NULL,
                contact_no       VARCHAR(20) NOT NULL,
                attendance_mode  VARCHAR(50) NOT NULL,
                purpose          VARCHAR(100) NOT NULL,
                attended_before  VARCHAR(100),
                notes            TEXT,
                registered_at    VARCHAR(60) NOT NULL
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    def execute(self, sql, params=()):
        # Run INSERT, UPDATE, DELETE queries
        conn   = self.__connect()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        return affected

    def fetchall(self, sql, params=()):
        # Run SELECT and return all rows as a list of dicts
        conn   = self.__connect()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    def fetchone(self, sql, params=()):
        # Run SELECT and return a single row as a dict
        conn   = self.__connect()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row


# ─────────────────────────────────────────────────────────────
#  PILLAR 1 — ABSTRACTION
#  BaseModel is the parent class. All models must follow
#  its rules by implementing validate() and to_dict().
# ─────────────────────────────────────────────────────────────
class BaseModel(ABC):

    def __init__(self, db: Database):
        self._db = db

    @abstractmethod
    def validate(self, data: dict) -> list:
        pass

    @abstractmethod
    def to_dict(self, row: dict) -> dict:
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


# ─────────────────────────────────────────────────────────────
#  PILLAR 2 — ENCAPSULATION
#  AdminAuth hides the credentials inside the class.
#  Nobody can directly access __USERNAME or __PASSWORD.
# ─────────────────────────────────────────────────────────────
class AdminAuth:
    __USERNAME = "admin"
    __PASSWORD = "ocrs2025"

    def check(self, username: str, password: str) -> bool:
        return username == self.__USERNAME and password == self.__PASSWORD

    @property
    def username(self):
        return self.__USERNAME


# ─────────────────────────────────────────────────────────────
#  PILLAR 3 — INHERITANCE  (inherits BaseModel)
#  PILLAR 4 — POLYMORPHISM (validate and to_dict are unique here)
# ─────────────────────────────────────────────────────────────
class RegistrationModel(BaseModel):

    def __generate_entry_no(self):
        # Auto-generate entry number like REG-2025-0001
        row  = self._db.fetchone("SELECT COUNT(*) as c FROM registrations")
        cnt  = row["c"] if row else 0
        return f"REG-{datetime.now().year}-{cnt + 1:04d}"

    def validate(self, data):
        # Check all required fields — return list of errors
        required = {
            "full_name":       "Full name",
            "student_id":      "Student / Employee ID",
            "email":           "Email",
            "department":      "Department",
            "year_level":      "Year level",
            "role":            "Role",
            "contact_no":      "Contact number",
            "attendance_mode": "Mode of attendance",
            "purpose":         "Purpose of attending",
        }
        return [f"{lbl} is required."
                for f, lbl in required.items()
                if not str(data.get(f, "")).strip()]

    def save(self, data):
        entry_no = self.__generate_entry_no()
        now      = datetime.now().strftime("%B %d, %Y - %I:%M %p")

        # Note: MySQL uses %s as placeholder (not ? like SQLite)
        self._db.execute(
            """INSERT INTO registrations
               (entry_no, full_name, student_id, email, department,
                year_level, role, contact_no, attendance_mode, purpose,
                attended_before, notes, registered_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                entry_no,
                data["full_name"].strip(),
                data["student_id"].strip(),
                data["email"].strip(),
                data["department"],
                data["year_level"],
                data["role"],
                data["contact_no"].strip(),
                data["attendance_mode"],
                data["purpose"],
                data.get("attended_before", "").strip(),
                data.get("dietary", "").strip(),
                now,
            )
        )
        return {"entry_no": entry_no, "registered_at": now}

    def all(self, limit=None, search="", department="", role="", attendance_mode=""):
        sql    = "SELECT * FROM registrations WHERE 1=1"
        params = []

        if search:
            sql += " AND (full_name LIKE %s OR email LIKE %s OR student_id LIKE %s)"
            params += [f"%{search}%"] * 3
        if department:
            sql += " AND department = %s"
            params.append(department)
        if role:
            sql += " AND role = %s"
            params.append(role)
        if attendance_mode:
            sql += " AND attendance_mode = %s"
            params.append(attendance_mode)

        sql += " ORDER BY id DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"

        return [self.to_dict(r) for r in self._db.fetchall(sql, tuple(params))]

    def delete(self, entry_no):
        self._db.execute(
            "DELETE FROM registrations WHERE entry_no = %s", (entry_no,)
        )

    def stats(self):
        total  = (self._db.fetchone("SELECT COUNT(*) as c FROM registrations") or {}).get("c", 0)
        online = (self._db.fetchone(
            "SELECT COUNT(*) as c FROM registrations WHERE attendance_mode = 'Online / Virtual'"
        ) or {}).get("c", 0)
        return {
            "total":      total,
            "online":     online,
            "in_person":  total - online,
            "by_dept":    self._db.fetchall("SELECT department, COUNT(*) as cnt FROM registrations GROUP BY department ORDER BY cnt DESC"),
            "by_role":    self._db.fetchall("SELECT role, COUNT(*) as cnt FROM registrations GROUP BY role ORDER BY cnt DESC"),
            "by_purpose": self._db.fetchall("SELECT purpose, COUNT(*) as cnt FROM registrations GROUP BY purpose ORDER BY cnt DESC"),
        }

    def count(self):
        row = self._db.fetchone("SELECT COUNT(*) as c FROM registrations")
        return row["c"] if row else 0

    def to_dict(self, row):
        return {
            "entry_no":        row["entry_no"],
            "full_name":       row["full_name"],
            "student_id":      row["student_id"],
            "email":           row["email"],
            "department":      row["department"],
            "year_level":      row["year_level"],
            "role":            row["role"],
            "contact_no":      row["contact_no"],
            "attendance_mode": row["attendance_mode"],
            "purpose":         row["purpose"],
            "attended_before": row.get("attended_before", ""),
            "notes":           row.get("notes", ""),
            "registered_at":   row["registered_at"],
        }


# ─────────────────────────────────────────────────────────────
#  FLASK APP
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "ocrs-secret-change-in-production"

db            = Database(DB_CONFIG)
registrations = RegistrationModel(db)
auth          = AdminAuth()


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ── Public routes ──────────────────────────────────────────────
@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/register")
def register():
    data   = request.get_json(silent=True) or {}
    errors = registrations.validate(data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    try:
        result = registrations.save(data)
        return jsonify({
            "ok":            True,
            "entry_no":      result["entry_no"],
            "registered_at": result["registered_at"],
            "name":          data["full_name"].strip()
        })
    except Exception as e:
        return jsonify({"ok": False, "errors": [str(e)]}), 500

@app.get("/api/registrations")
def get_registrations():
    limit = request.args.get("limit")
    return jsonify({
        "total":   registrations.count(),
        "entries": registrations.all(limit=int(limit) if limit else None)
    })


# ── Admin routes ───────────────────────────────────────────────
@app.get("/admin/login")
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")

@app.post("/admin/login")
def admin_login_post():
    if auth.check(request.form.get("username", ""), request.form.get("password", "")):
        session["admin_logged_in"] = True
        return redirect(url_for("admin_dashboard"))
    flash("Invalid username or password.")
    return redirect(url_for("admin_login"))

@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.get("/admin")
@admin_required
def admin_dashboard():
    search          = request.args.get("search", "")
    department      = request.args.get("department", "")
    role            = request.args.get("role", "")
    attendance_mode = request.args.get("attendance_mode", "")
    return render_template("admin.html",
        entries         = registrations.all(search=search, department=department,
                                            role=role, attendance_mode=attendance_mode),
        stats           = registrations.stats(),
        search          = search,
        filter_dept     = department,
        filter_role     = role,
        filter_mode     = attendance_mode,
    )

@app.post("/admin/delete/<entry_no>")
@admin_required
def admin_delete(entry_no):
    registrations.delete(entry_no)
    return redirect(request.referrer or url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
