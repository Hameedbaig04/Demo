import os
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this-before-deploying")
database_url = os.environ.get("DATABASE_URL", "sqlite:///attendance_web.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="manager")
    active = db.Column(db.Boolean, nullable=False, default=True)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), default="")
    job_title = db.Column(db.String(100), default="")
    basic_salary = db.Column(db.Float, nullable=False, default=0)
    allowance = db.Column(db.Float, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    check_in = db.Column(db.String(5), default="")
    check_out = db.Column(db.String(5), default="")
    recorded_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    employee = db.relationship("Employee")
    __table_args__ = (db.UniqueConstraint("employee_id", "work_date", name="uq_employee_workdate"),)

STATUSES = ["Present", "Absent", "Leave", "Holiday", "Weekly Off"]

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access is required.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_user():
    return {"current_user": session.get("username"), "current_role": session.get("role")}

@app.route("/")
def home():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip(), active=True).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            session.clear()
            session.update(user_id=user.id, username=user.username, role=user.role)
            return redirect(url_for("dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    total = Employee.query.filter_by(active=True).count()
    present = Attendance.query.join(Employee).filter(Attendance.work_date == today, Attendance.status == "Present", Employee.active == True).count()
    absent = Attendance.query.join(Employee).filter(Attendance.work_date == today, Attendance.status == "Absent", Employee.active == True).count()
    return render_template("dashboard.html", total=total, present=present, absent=absent, today=today)

@app.route("/employees")
@login_required
def employees():
    q = request.args.get("q", "").strip()
    query = Employee.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Employee.employee_code.ilike(like), Employee.full_name.ilike(like), Employee.department.ilike(like)))
    return render_template("employees.html", employees=query.order_by(Employee.active.desc(), Employee.full_name).all(), q=q)

@app.route("/employees/add", methods=["GET", "POST"])
@admin_required
def add_employee():
    if request.method == "POST":
        try:
            code = request.form["employee_code"].strip()
            name = request.form["full_name"].strip()
            salary = float(request.form.get("basic_salary") or 0)
            allowance = float(request.form.get("allowance") or 0)
            if not code or not name or salary < 0 or allowance < 0:
                raise ValueError()
            emp = Employee(employee_code=code, full_name=name, department=request.form.get("department","").strip(),
                           job_title=request.form.get("job_title","").strip(), basic_salary=salary, allowance=allowance)
            db.session.add(emp)
            db.session.commit()
            flash("Employee added.", "success")
            return redirect(url_for("employees"))
        except (ValueError, KeyError):
            db.session.rollback()
            flash("Check the required fields and salary amounts.", "error")
        except Exception:
            db.session.rollback()
            flash("That employee ID may already exist.", "error")
    return render_template("employee_form.html")

@app.route("/employees/<int:employee_id>/toggle", methods=["POST"])
@admin_required
def toggle_employee(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    emp.active = not emp.active
    db.session.commit()
    flash("Employee status updated.", "success")
    return redirect(url_for("employees"))

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    try:
        selected = date.fromisoformat(request.values.get("work_date", date.today().isoformat()))
    except ValueError:
        selected = date.today()
        flash("Invalid date; showing today.", "error")
    active_employees = Employee.query.filter_by(active=True).order_by(Employee.full_name).all()
    existing = {a.employee_id: a for a in Attendance.query.filter_by(work_date=selected).all()}
    if request.method == "POST":
        for emp in active_employees:
            status = request.form.get(f"status_{emp.id}", "")
            if status not in STATUSES:
                continue
            check_in = request.form.get(f"in_{emp.id}", "").strip()
            check_out = request.form.get(f"out_{emp.id}", "").strip()
            for value in (check_in, check_out):
                if value and (len(value) != 5 or value[2] != ":" or not value[:2].isdigit() or not value[3:].isdigit() or int(value[:2]) > 23 or int(value[3:]) > 59):
                    flash(f"Invalid time for {emp.full_name}; use HH:MM.", "error")
                    return redirect(url_for("attendance", work_date=selected.isoformat()))
            row = Attendance.query.filter_by(employee_id=emp.id, work_date=selected).first()
            if row:
                row.status, row.check_in, row.check_out, row.recorded_by = status, check_in, check_out, session["user_id"]
            else:
                db.session.add(Attendance(employee_id=emp.id, work_date=selected, status=status,
                                          check_in=check_in, check_out=check_out, recorded_by=session["user_id"]))
        db.session.commit()
        flash(f"Attendance saved for {selected.isoformat()}.", "success")
        return redirect(url_for("attendance", work_date=selected.isoformat()))
    return render_template("attendance.html", employees=active_employees, records=existing, selected=selected, statuses=STATUSES)

@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "manager")
        if not username or len(password) < 10 or role not in ("admin", "manager"):
            flash("Enter a username and a password of at least 10 characters.", "error")
        elif User.query.filter_by(username=username).first():
            flash("That username already exists.", "error")
        else:
            db.session.add(User(username=username, password_hash=generate_password_hash(password), role=role))
            db.session.commit()
            flash("User created.", "success")
    return render_template("users.html", users=User.query.order_by(User.username).all())

with app.app_context():
    db.create_all()
    # Demo-only starter login. Change it immediately after first login.
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password_hash=generate_password_hash("ChangeMe123!"), role="admin"))
        db.session.commit()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
