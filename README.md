# AI-Based Student Performance Prediction System

An AI-powered web application that predicts student academic performance using machine learning. Built for Nigerian university grading standards, it enables lecturers to identify at-risk students, generate intervention recommendations, and export detailed reports — before final results are released.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Default Credentials](#default-credentials)
- [Grading System](#grading-system)
- [File Upload Format](#file-upload-format)
- [Machine Learning Models](#machine-learning-models)
- [API Endpoints](#api-endpoints)
- [Roles and Permissions](#roles-and-permissions)
- [Email Notifications](#email-notifications)
- [Report Generation](#report-generation)
- [Known Limitations](#known-limitations)
- [Future Work](#future-work)

---

## Overview

The Student Performance Prediction System (SPPS) is a web-based decision-support tool for lecturers and academic administrators. It analyses student assessment data — examination scores, continuous assessment tests, assignment scores, and attendance — and generates predictions using four trained machine learning models.

The system is calibrated to the Nigerian university grading convention (Examination 60%, Tests 20%, Assignments 10%, Attendance 10%) but allows each lecturer to configure their own grading scheme. Predictions include pass/fail status, letter grade (A–F), at-risk classification, and a numerical score estimate. Each at-risk student also receives prioritised intervention recommendations.

---

## Features

- **User Authentication** — Role-based access for Admins and Lecturers with bcrypt password hashing and first-login password setup
- **Single Student Prediction** — Interactive slider-based form with instant prediction results and component breakdown
- **Bulk Upload** — CSV and Excel file upload with row-level validation and batch prediction for entire class cohorts
- **Dashboard** — Class-wide statistics including pass rate, average score, at-risk count, and grade distribution charts
- **All Students Table** — Searchable and filterable student list with priority badges and per-student detail modal
- **Intervention Recommendations** — Rule-based engine generating LOW / MEDIUM / HIGH / CRITICAL priority guidance per at-risk student
- **Report Generation** — Individual student PDF reports and class-wide Excel workbooks (three sheets: all students, summary with chart, at-risk list)
- **Custom Grading Scheme** — Configurable weights, number of tests and assignments, grade boundaries, and pass mark per lecturer
- **Email Notifications** — Automated Gmail SMTP alerts when at-risk student count exceeds a configurable threshold
- **Admin Panel** — Create, deactivate, and reset passwords for lecturer accounts
- **CSV Template Download** — Dynamically generated template reflecting the lecturer's active grading scheme

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.8+, Flask 2.3+ |
| Machine Learning | Scikit-learn, NumPy, Pandas |
| Frontend | HTML5, CSS3, JavaScript (ES6+) |
| Charts | Chart.js |
| PDF Generation | ReportLab |
| Excel Generation | XlsxWriter |
| Excel Parsing | OpenPyXL, xlrd |
| Authentication | bcrypt, Flask sessions |
| Email | smtplib (Gmail SMTP) |
| Model Persistence | Joblib |
| Font | Geist (Google Fonts) |

---

## Project Structure

```
student-performance-system/
│
├── app.py                  # Flask application and all API routes
├── ml_models.py            # ML model definitions, training, and prediction logic
├── auth.py                 # User management, authentication, role decorators
├── recommendations.py      # Rule-based intervention recommendation engine
├── notifications.py        # Gmail SMTP email alert system
├── reports.py              # PDF and Excel report generation
├── requirements.txt        # Python package dependencies
├── users.json              # Persistent user account store (auto-created on first run)
│
├── models/                 # Serialised trained model files (auto-created on first run)
│   ├── scaler.pkl
│   ├── pass_fail_model.pkl
│   ├── grade_model.pkl
│   ├── at_risk_model.pkl
│   └── score_model.pkl
│
├── templates/
│   ├── index.html          # Main application interface
│   └── login.html          # Login and first-login password setup page
│
└── static/
    ├── css/
    │   └── style.css       # Application stylesheet
    └── js/
        └── app.js          # Frontend JavaScript logic
```

---

## Prerequisites

- Python 3.8 or higher
- pip
- A Gmail account with an App Password (only required if using email notifications)

---

## Installation

### 1. Clone or download the project

```bash
git clone https://github.com/your-username/student-performance-system.git
cd student-performance-system
```

Or download and extract the ZIP, then navigate into the folder.

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Train the machine learning models

This only needs to be done once. The trained models are saved to the `models/` folder.

```bash
python ml_models.py
```

You should see output confirming each model's training accuracy before the script exits.

---

## Running the Application

```bash
python app.py
```

On startup, the application will:
1. Seed the default admin account if it does not already exist
2. Load the trained models from the `models/` folder (or train them if missing)
3. Start the Flask development server

Open your browser and navigate to:

```
http://localhost:5000
```

---

## Default Credentials

A default administrator account is created automatically on first run.

| Field | Value |
|-------|-------|
| Username | `CU_Admin` |
| Password | `Admin123!` |

> **Change this password after your first login.**

Lecturer accounts are created by the Admin through the Admin Panel. New lecturer accounts are assigned a default password and flagged to require a password change on first login.

---

## Grading System

The default grading scheme follows the Nigerian university standard:

| Component | Weight |
|-----------|--------|
| Examination | 60% |
| Tests | 20% |
| Assignments | 10% |
| Attendance | 10% |

**Grade boundaries (default):**

| Grade | Score Range | Status |
|-------|------------|--------|
| A | 70 – 100 | Pass |
| B | 60 – 69 | Pass |
| C | 50 – 59 | Pass |
| D | 45 – 49 | Pass |
| F | 0 – 44 | Fail |

Each lecturer can customise weights, the number of tests and assignments (1–3 each), grade boundaries, and the pass mark from the Settings tab. Changes apply immediately to all subsequent predictions and uploads.

**Score formula:**

```
Final Score = (Exam × 0.60) + (Avg Test × 0.20) + (Avg Assignment × 0.10) + (Attendance × 0.10)
```

---

## File Upload Format

Download the CSV template from the Bulk Upload tab. The template is dynamically generated to reflect your active grading scheme.

### Required columns

```
student_id       (optional)
student_name     (required)
attendance       (0–100)
test1            (0–100)
test2            (0–100)  — only if scheme uses 2+ tests
test3            (0–100)  — only if scheme uses 3 tests
assignment1      (0–100)
assignment2      (0–100)  — only if scheme uses 2+ assignments
assignment3      (0–100)  — only if scheme uses 3 assignments
exam_score       (0–100)
```

### Example

```csv
student_id,student_name,attendance,test1,test2,test3,assignment1,assignment2,assignment3,exam_score
2023001,John Doe,85.5,78,82,75,88,85,90,80
2023002,Jane Smith,92.0,88,91,87,93,89,95,92
```

### Validation rules

- All numeric fields must be between 0 and 100
- `student_name` cannot be empty
- Missing required columns will block the upload entirely
- Invalid individual rows are flagged with specific error messages; valid rows are still processed

---

## Machine Learning Models

Four models are trained and used for prediction:

| Model | Algorithm | Task | Accuracy |
|-------|-----------|------|----------|
| Pass/Fail | Random Forest Classifier | Binary classification | 94.00% |
| Grade Category | Gradient Boosting Classifier | 5-class classification (A–F) | 88.00% |
| At-Risk | Random Forest Classifier | Binary classification | 91.00% |
| Score | Random Forest Regressor | Continuous score prediction | R² = 0.87 |

Models are trained on a synthetically generated dataset of 500 student records drawn from mixed Beta distributions across three performance tiers (high, average, and struggling). Features are normalised using `StandardScaler` before training. The dataset is split 80/20 using stratified sampling for classification tasks.

Trained models are serialised as `.pkl` files using Joblib and loaded once at application start.

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/login` | Login page |
| POST | `/api/auth/login` | Authenticate user |
| POST | `/api/auth/logout` | End session |
| GET | `/api/auth/me` | Get current user info |
| POST | `/api/auth/set-password` | Set password (first login) |

### Prediction

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/predict` | Single student prediction |
| POST | `/api/upload-bulk` | Bulk file upload and batch prediction |
| GET | `/api/dashboard` | Dashboard statistics |
| GET | `/api/students` | All student records for current user |
| GET | `/api/student/<id>` | Individual student record |
| POST | `/api/clear` | Clear all session data |
| GET | `/api/template` | Download CSV template |

### Reports and Exports

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export/student/<id>` | Download individual student PDF |
| GET | `/api/export/class` | Download class Excel workbook |

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get current user settings |
| POST | `/api/settings/scheme` | Save grading scheme |
| POST | `/api/settings/email` | Save email notification settings |
| POST | `/api/settings/email/test` | Send test email |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users` | List all lecturer accounts |
| POST | `/api/admin/users` | Create lecturer account |
| PUT | `/api/admin/users/<id>` | Update user details |
| POST | `/api/admin/users/<id>/deactivate` | Deactivate account |
| POST | `/api/admin/users/<id>/reset-password` | Reset password (force change on next login) |

---

## Roles and Permissions

| Feature | Admin | Lecturer |
|---------|-------|----------|
| Login | ✓ | ✓ |
| Dashboard | ✓ | ✓ |
| Single prediction | ✓ | ✓ |
| Bulk upload | ✓ | ✓ |
| All Students table | ✓ | ✓ |
| Reports | ✓ | ✓ |
| Settings (own scheme) | ✓ | ✓ |
| Email notifications | ✓ | ✓ |
| Admin Panel | ✓ | ✗ |
| Create lecturer accounts | ✓ | ✗ |
| Deactivate accounts | ✓ | ✗ |

Each lecturer's student data is isolated — lecturers cannot see each other's records.

---

## Email Notifications

The system uses Gmail SMTP to send automated alerts. Notifications are sent when the number of at-risk students in a batch exceeds your configured threshold (default: 10).

### Setup

1. Go to the **Settings** tab
2. Enable notifications using the toggle
3. Set your at-risk threshold
4. Enter your recipient email and Gmail sender address
5. Generate a **Gmail App Password** from your Google Account under Security → Two-Factor Authentication → App Passwords
6. Enter the App Password in the password field
7. Click **Save Settings**, then **Send Test Email** to verify

> Email sending runs in a background thread and will not block or delay prediction results if it fails.

---

## Report Generation

### Individual Student PDF

Contains:
- Student information and key prediction results
- Score breakdown table with component contributions
- Individual test and assignment scores
- Risk factors identified
- Prioritised intervention recommendations

Download from the **Reports** tab or directly from any row in the **All Students** table.

### Class Performance Excel

Contains three worksheets:
- **All Students** — complete prediction data with colour-coded grades and statuses
- **Summary** — aggregate statistics and an embedded grade distribution chart
- **At-Risk Students** — filtered list with risk factors and recommendation priority

Download from the **Reports** tab.

---

## Known Limitations

- **No persistent database** — all student data is stored in memory and lost when the server restarts. This is a deliberate scope decision; database integration is the primary next step.
- **Synthetic training data** — models were trained on artificially generated records. Accuracy may improve when retrained on real institutional data.
- **Manual SMTP setup** — email notifications require each lecturer to configure their own Gmail App Password. A centralised email service (e.g. SendGrid) would be more suitable for institutional deployment.
- **No historical tracking** — the system cannot currently track a student's performance across multiple semesters or uploads.

---

## Future Work

1. **SQLite database integration** — persistent storage for student records, upload history, and semester-on-semester performance tracking
2. **Retrain on real data** — replace synthetic training data with actual institutional records to improve domain-specific accuracy
3. **Student-facing portal** — read-only access for students to view their own predictions and recommendations
4. **Centralised email delivery** — replace per-user Gmail SMTP with a transactional email service
5. **Performance trend analysis** — visualise a student's trajectory across multiple assessment periods

---

## Dependencies

```
Flask==2.3.3
Flask-Cors==4.0.0
pandas==2.0.3
numpy==1.24.3
scikit-learn==1.3.0
joblib==1.3.2
matplotlib==3.7.2
seaborn==0.12.2
openpyxl==3.1.2
xlrd==2.0.1
xlsxwriter==3.1.9
reportlab==4.0.5
bcrypt==4.1.2
```

Install all dependencies with:

```bash
pip install -r requirements.txt
```

---

## License

This project was developed as a final year undergraduate project at Caleb University, Imota, Lagos, in partial fulfilment of the requirements for the award of a Bachelor of Science (B.Sc.) in Computer Science.

**Supervisor:** Dr. Adeniyi Akanni
**Author:** Abajo Oluwaferanmipupo David · 22/9622 · June 2026
