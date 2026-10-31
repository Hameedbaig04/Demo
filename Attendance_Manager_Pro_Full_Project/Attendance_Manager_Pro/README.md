# Attendance Manager Pro

Windows desktop prototype for employee records and daily attendance.

## Included in this build
- Login screen with an initial administrator account
- Employee directory: add, edit, search, deactivate/reactivate
- Daily attendance: choose a date, mark each active employee, enter check-in/check-out, and save
- Local SQLite database stored beside `main.py`

## Not implemented yet
- Overtime calculations and approvals
- Payroll generation and salary rules
- Admin/manager user creation and permissions UI
- Shared multi-computer database access

These modules will be added and tested in later builds. Do not use this prototype as the sole official payroll or attendance record yet.

## Requirements
- Windows 10 or newer
- Python 3.10 or newer

## First-time setup
1. Install Python from https://www.python.org/downloads/.
2. During installation, enable **Add Python to PATH**.
3. Open this extracted folder in File Explorer.
4. Double-click `install_and_run.bat`, or open Command Prompt in this folder and run:

   ```bat
   py -m pip install -r requirements.txt
   py main.py
   ```

## Initial login
- Username: `admin`
- Password: `ChangeMe123!`

Change the temporary password before using real employee information. This prototype currently stores its database locally in `attendance_manager.db`.

## Updating without losing local data
Close the app before updating. Keep a backup of `attendance_manager.db`. When extracting a newer ZIP into the same project folder, allow `main.py` and other application files to be replaced, but do not delete or replace `attendance_manager.db`.
