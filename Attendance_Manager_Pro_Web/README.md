# Attendance Manager Pro — Web Testing Build

## Current features
- Login/logout and admin/manager roles
- Dashboard with today's attendance counts
- Employee directory, add/deactivate/reactivate
- Daily attendance with status and check-in/check-out
- Admin can create manager/admin logins

Overtime and payroll are not implemented in this web build yet.

## Run locally on Windows
1. Install Python 3.11 or newer.
2. Extract this ZIP to a folder.
3. Open Command Prompt in that folder.
4. Run:
   `py -m venv .venv`
   `.venv\Scripts\activate`
   `py -m pip install -r requirements.txt`
   `py app.py`
5. Open http://127.0.0.1:5000

Initial test login: `admin` / `ChangeMe123!`
Change the default login immediately. This local test uses a local SQLite database.

## Important
- Do not enter real employee salaries or personal information into a public test deployment.
- The free Render PostgreSQL database is temporary (30 days) and has no backups. Export data before expiry.
- Set a strong SECRET_KEY and use PostgreSQL for cloud deployment.
- The desktop app's SQLite database is NOT automatically imported by this web build. Migration must be done deliberately after checking the old database and making a backup.
