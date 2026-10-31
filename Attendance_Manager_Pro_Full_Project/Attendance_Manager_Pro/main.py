import sqlite3
import hashlib
import os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import date

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "attendance_manager.db")

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex(), digest.hex()

def verify_password(password, salt_hex, hash_hex):
    salt = bytes.fromhex(salt_hex)
    _, calculated = hash_password(password, salt)
    return calculated == hash_hex

def initialize_database():
    with connect_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'manager')),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            department TEXT,
            job_title TEXT,
            basic_salary REAL NOT NULL DEFAULT 0,
            allowance REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN
                ('Present', 'Absent', 'Leave', 'Holiday', 'Weekly Off')),
            check_in TEXT, check_out TEXT, notes TEXT, recorded_by INTEGER,
            UNIQUE(employee_id, work_date),
            FOREIGN KEY(employee_id) REFERENCES employees(id),
            FOREIGN KEY(recorded_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS overtime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            hours REAL NOT NULL CHECK(hours >= 0),
            hourly_rate REAL NOT NULL DEFAULT 0,
            notes TEXT, recorded_by INTEGER,
            FOREIGN KEY(employee_id) REFERENCES employees(id),
            FOREIGN KEY(recorded_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            pay_month TEXT NOT NULL,
            basic_salary REAL NOT NULL,
            allowances REAL NOT NULL DEFAULT 0,
            overtime_pay REAL NOT NULL DEFAULT 0,
            deductions REAL NOT NULL DEFAULT 0,
            net_pay REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, pay_month),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        """)
        if not conn.execute("SELECT id FROM users WHERE username='admin'").fetchone():
            salt, digest = hash_password("ChangeMe123!")
            conn.execute(
                "INSERT INTO users(username,password_salt,password_hash,role) VALUES(?,?,?,'admin')",
                ("admin", salt, digest)
            )

def authenticate(username, password):
    with connect_db() as conn:
        row = conn.execute(
            "SELECT id,username,password_salt,password_hash,role FROM users WHERE username=? AND active=1",
            (username.strip(),)
        ).fetchone()
    if not row or not verify_password(password, row[2], row[3]):
        return None
    return {"id": row[0], "username": row[1], "role": row[4]}

class EmployeeDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, employee=None, on_save=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("430x560")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_save = on_save
        self.employee = employee

        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=23, weight="bold")).pack(pady=(22, 14))
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=28)

        self.fields = {}
        field_specs = [
            ("Employee ID *", "employee_code"),
            ("Full name *", "full_name"),
            ("Department", "department"),
            ("Job title", "job_title"),
            ("Basic salary (AED)", "basic_salary"),
            ("Allowances (AED)", "allowance"),
        ]
        values = employee or {}
        for label, key in field_specs:
            ctk.CTkLabel(form, text=label).pack(anchor="w", pady=(7, 2))
            entry = ctk.CTkEntry(form, height=36, placeholder_text=label)
            entry.pack(fill="x")
            value = values.get(key, "")
            if key in ("basic_salary", "allowance") and value == "":
                value = "0"
            if value is not None:
                entry.insert(0, str(value))
            self.fields[key] = entry

        ctk.CTkButton(self, text="Save employee", height=42, command=self.save).pack(fill="x", padx=28, pady=22)

    def save(self):
        data = {key: entry.get().strip() for key, entry in self.fields.items()}
        if not data["employee_code"] or not data["full_name"]:
            messagebox.showwarning("Missing information", "Employee ID and full name are required.", parent=self)
            return
        try:
            data["basic_salary"] = float(data["basic_salary"] or 0)
            data["allowance"] = float(data["allowance"] or 0)
            if data["basic_salary"] < 0 or data["allowance"] < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid amount", "Salary and allowances must be non-negative numbers.", parent=self)
            return
        try:
            self.on_save(data)
            self.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate employee ID", "That Employee ID already exists. Use a unique ID.", parent=self)

class AttendanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Attendance Manager Pro")
        self.geometry("1120x720")
        self.minsize(900, 600)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.current_user = None
        self.show_login()

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear()
        outer = ctk.CTkFrame(self, corner_radius=18)
        outer.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(outer, text="ATTENDANCE MANAGER PRO", font=ctk.CTkFont(size=24, weight="bold")).pack(padx=42, pady=(32, 8))
        ctk.CTkLabel(outer, text="Sign in to continue", text_color=("gray40", "gray70")).pack(pady=(0, 22))
        self.username_entry = ctk.CTkEntry(outer, width=300, height=40, placeholder_text="Username")
        self.username_entry.pack(padx=35, pady=8)
        self.password_entry = ctk.CTkEntry(outer, width=300, height=40, placeholder_text="Password", show="*")
        self.password_entry.pack(padx=35, pady=8)
        self.password_entry.bind("<Return>", lambda event: self.login())
        ctk.CTkButton(outer, text="Sign in", width=300, height=40, command=self.login).pack(padx=35, pady=(16, 12))
        ctk.CTkLabel(outer, text="First login: admin  |  ChangeMe123!", font=ctk.CTkFont(size=12), text_color=("gray40", "gray70")).pack(pady=(0, 28))

    def login(self):
        user = authenticate(self.username_entry.get(), self.password_entry.get())
        if not user:
            messagebox.showerror("Sign-in failed", "Incorrect username or password.")
            return
        self.current_user = user
        self.show_dashboard()

    def show_dashboard(self):
        self.clear()
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        ctk.CTkLabel(sidebar, text="ATTENDANCE\nMANAGER PRO", font=ctk.CTkFont(size=19, weight="bold")).pack(pady=(28, 35))
        pages = ["Dashboard", "Employees", "Attendance", "Overtime", "Payroll", "User management"]
        for page in pages:
            if page == "User management" and self.current_user["role"] != "admin":
                continue
            ctk.CTkButton(
                sidebar, text=page, anchor="w", fg_color="transparent",
                text_color=("gray10", "gray90"), hover_color=("gray80", "gray25"),
                command=lambda p=page: self.show_page(p)
            ).pack(fill="x", padx=14, pady=5)
        ctk.CTkButton(sidebar, text="Sign out", fg_color="#9b3030", hover_color="#7c2525", command=self.show_login).pack(side="bottom", fill="x", padx=14, pady=20)
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True)
        top = ctk.CTkFrame(main, corner_radius=0)
        top.pack(fill="x")
        ctk.CTkLabel(top, text=f"Welcome, {self.current_user['username']}  ({self.current_user['role'].title()})", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=25, pady=22)
        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=25, pady=25)
        self.show_page("Dashboard")

    def show_page(self, page):
        for widget in self.content.winfo_children():
            widget.destroy()
        if page == "Employees":
            self.show_employees()
            return
        if page == "Attendance":
            self.show_attendance()
            return
        ctk.CTkLabel(self.content, text=page, font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", pady=(5, 18))
        if page == "Dashboard":
            with connect_db() as conn:
                count = conn.execute("SELECT COUNT(*) FROM employees WHERE active=1").fetchone()[0]
            ctk.CTkLabel(self.content, text="Your attendance management workspace is ready.", font=ctk.CTkFont(size=16)).pack(anchor="w", pady=5)
            cards = ctk.CTkFrame(self.content, fg_color="transparent")
            cards.pack(fill="x", pady=20)
            for title, value in [("Active employees", str(count)), ("Present today", "—"), ("Absent today", "—"), ("Payroll", "Not generated")]:
                card = ctk.CTkFrame(cards, corner_radius=12)
                card.pack(side="left", expand=True, fill="x", padx=6)
                ctk.CTkLabel(card, text=title).pack(padx=15, pady=(18, 5))
                ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=25, weight="bold")).pack(padx=15, pady=(0, 18))
        else:
            ctk.CTkLabel(self.content, text=f"The {page.lower()} module is coming in the next build.", font=ctk.CTkFont(size=15)).pack(anchor="w")


    def show_attendance(self):
        heading = ctk.CTkFrame(self.content, fg_color="transparent")
        heading.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(heading, text="Daily Attendance", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")

        date_row = ctk.CTkFrame(self.content, fg_color="transparent")
        date_row.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(date_row, text="Work date (YYYY-MM-DD):").pack(side="left", padx=(0, 8))
        self.attendance_date = ctk.CTkEntry(date_row, width=150)
        self.attendance_date.pack(side="left")
        self.attendance_date.insert(0, date.today().isoformat())
        ctk.CTkButton(date_row, text="Load date", width=100, command=self.load_attendance_rows).pack(side="left", padx=8)

        self.attendance_rows = ctk.CTkScrollableFrame(self.content, label_text="Mark each employee")
        self.attendance_rows.pack(fill="both", expand=True, pady=(0, 12))
        ctk.CTkButton(self.content, text="Save all attendance", height=42, command=self.save_attendance_rows).pack(anchor="e")
        self.load_attendance_rows()

    def load_attendance_rows(self):
        try:
            selected_date = self.attendance_date.get().strip()
            date.fromisoformat(selected_date)
        except ValueError:
            messagebox.showerror("Invalid date", "Enter the date as YYYY-MM-DD, for example 2026-10-31.")
            return

        for widget in self.attendance_rows.winfo_children():
            widget.destroy()
        with connect_db() as conn:
            employees = conn.execute(
                "SELECT id, employee_code, full_name FROM employees WHERE active=1 ORDER BY full_name COLLATE NOCASE"
            ).fetchall()
            existing = {
                row[0]: row[1:]
                for row in conn.execute(
                    "SELECT employee_id, status, check_in, check_out FROM attendance WHERE work_date=?",
                    (selected_date,)
                ).fetchall()
            }

        self.attendance_controls = {}
        if not employees:
            ctk.CTkLabel(self.attendance_rows, text="No active employees. Add an employee first.").pack(pady=25)
            return

        header = ctk.CTkFrame(self.attendance_rows, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(4, 8))
        for label, width in [("Employee", 250), ("Status", 150), ("Check-in", 115), ("Check-out", 115)]:
            ctk.CTkLabel(header, text=label, width=width, anchor="w",
                         font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)

        for emp_id, emp_code, name in employees:
            saved = existing.get(emp_id, ("-- Select --", "", ""))
            row = ctk.CTkFrame(self.attendance_rows, corner_radius=8)
            row.pack(fill="x", padx=5, pady=4)
            ctk.CTkLabel(row, text=f"{emp_code} · {name}", width=250, anchor="w").pack(side="left", padx=8, pady=10)

            status = ctk.CTkOptionMenu(
                row, values=["-- Select --", "Present", "Absent", "Leave", "Holiday", "Weekly Off"], width=140
            )
            status.set(saved[0] or "Present")
            status.pack(side="left", padx=4)

            check_in = ctk.CTkEntry(row, width=105, placeholder_text="09:00")
            check_in.pack(side="left", padx=4)
            if saved[1]:
                check_in.insert(0, saved[1])

            check_out = ctk.CTkEntry(row, width=105, placeholder_text="18:00")
            check_out.pack(side="left", padx=4)
            if saved[2]:
                check_out.insert(0, saved[2])

            self.attendance_controls[emp_id] = (status, check_in, check_out)

    def save_attendance_rows(self):
        try:
            selected_date = self.attendance_date.get().strip()
            date.fromisoformat(selected_date)
        except ValueError:
            messagebox.showerror("Invalid date", "Enter the date as YYYY-MM-DD.")
            return

        if not getattr(self, "attendance_controls", None):
            messagebox.showinfo("Nothing to save", "There are no active employees to record.")
            return

        try:
            with connect_db() as conn:
                for emp_id, controls in self.attendance_controls.items():
                    status = controls[0].get()
                    if status == "-- Select --":
                        raise ValueError("Please choose an attendance status for every employee before saving.")
                    check_in = controls[1].get().strip() or None
                    check_out = controls[2].get().strip() or None
                    for value, label in [(check_in, "Check-in"), (check_out, "Check-out")]:
                        if value and (len(value) != 5 or value[2] != ":" or not value[:2].isdigit() or not value[3:].isdigit() or int(value[:2]) > 23 or int(value[3:]) > 59):
                            raise ValueError(f"{label} time must use 24-hour HH:MM format, e.g. 09:00.")
                    conn.execute(
                        """INSERT INTO attendance
                           (employee_id, work_date, status, check_in, check_out, recorded_by)
                           VALUES (?, ?, ?, ?, ?, ?)
                           ON CONFLICT(employee_id, work_date) DO UPDATE SET
                           status=excluded.status, check_in=excluded.check_in,
                           check_out=excluded.check_out, recorded_by=excluded.recorded_by""",
                        (emp_id, selected_date, status, check_in, check_out, self.current_user["id"])
                    )
        except ValueError as error:
            messagebox.showerror("Check the time", str(error))
            return

        messagebox.showinfo("Saved", f"Attendance saved for {selected_date}.")

    def show_employees(self):
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(header, text="Employees", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")
        if self.current_user["role"] == "admin":
            ctk.CTkButton(header, text="+ Add employee", command=self.add_employee).pack(side="right")

        self.search_entry = ctk.CTkEntry(self.content, placeholder_text="Search by employee ID, name or department...")
        self.search_entry.pack(fill="x", pady=(0, 12))
        self.search_entry.bind("<KeyRelease>", lambda event: self.load_employees())

        self.employee_list = ctk.CTkScrollableFrame(self.content, label_text="Employee directory")
        self.employee_list.pack(fill="both", expand=True)
        self.load_employees()

    def load_employees(self):
        for widget in self.employee_list.winfo_children():
            widget.destroy()
        query = self.search_entry.get().strip()
        with connect_db() as conn:
            rows = conn.execute(
                """SELECT id, employee_code, full_name, department, job_title,
                          basic_salary, allowance, active
                   FROM employees
                   WHERE employee_code LIKE ? OR full_name LIKE ? OR department LIKE ?
                   ORDER BY active DESC, full_name COLLATE NOCASE""",
                (f"%{query}%", f"%{query}%", f"%{query}%")
            ).fetchall()

        if not rows:
            ctk.CTkLabel(self.employee_list, text="No employees found. Click '+ Add employee' to create your first record.").pack(pady=30)
            return

        for row in rows:
            emp = {
                "id": row[0], "employee_code": row[1], "full_name": row[2],
                "department": row[3] or "", "job_title": row[4] or "",
                "basic_salary": row[5], "allowance": row[6], "active": row[7]
            }
            line = ctk.CTkFrame(self.employee_list, corner_radius=10)
            line.pack(fill="x", padx=5, pady=5)
            info = ctk.CTkFrame(line, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=12, pady=10)
            ctk.CTkLabel(info, text=f"{emp['employee_code']}  |  {emp['full_name']}", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w")
            detail = f"{emp['department'] or 'No department'} · {emp['job_title'] or 'No job title'} · Basic AED {emp['basic_salary']:,.2f} · Allowance AED {emp['allowance']:,.2f}"
            if not emp["active"]:
                detail += " · INACTIVE"
            ctk.CTkLabel(info, text=detail, text_color=("gray40", "gray70"), font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(3, 0))
            if self.current_user["role"] == "admin":
                ctk.CTkButton(line, text="Edit", width=65, command=lambda e=emp: self.edit_employee(e)).pack(side="right", padx=(4, 10))
                action = "Reactivate" if not emp["active"] else "Deactivate"
                ctk.CTkButton(line, text=action, width=95, fg_color=("gray65", "gray35"), command=lambda e=emp: self.toggle_employee(e)).pack(side="right", padx=4)

    def add_employee(self):
        EmployeeDialog(self, "Add employee", on_save=self.insert_employee)

    def insert_employee(self, data):
        with connect_db() as conn:
            conn.execute(
                """INSERT INTO employees
                   (employee_code,full_name,department,job_title,basic_salary,allowance)
                   VALUES(?,?,?,?,?,?)""",
                (data["employee_code"], data["full_name"], data["department"],
                 data["job_title"], data["basic_salary"], data["allowance"])
            )
        self.load_employees()

    def edit_employee(self, employee):
        def update(data):
            with connect_db() as conn:
                conn.execute(
                    """UPDATE employees SET employee_code=?,full_name=?,department=?,
                       job_title=?,basic_salary=?,allowance=? WHERE id=?""",
                    (data["employee_code"], data["full_name"], data["department"],
                     data["job_title"], data["basic_salary"], data["allowance"], employee["id"])
                )
            self.load_employees()
        EmployeeDialog(self, "Edit employee", employee=employee, on_save=update)

    def toggle_employee(self, employee):
        new_state = 0 if employee["active"] else 1
        action = "deactivate" if new_state == 0 else "reactivate"
        if not messagebox.askyesno("Confirm", f"Do you want to {action} {employee['full_name']}?"):
            return
        with connect_db() as conn:
            conn.execute("UPDATE employees SET active=? WHERE id=?", (new_state, employee["id"]))
        self.load_employees()

if __name__ == "__main__":
    initialize_database()
    app = AttendanceApp()
    app.mainloop()
