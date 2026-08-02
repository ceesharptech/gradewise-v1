# Agent Context

## Overview

- Flask-based web app for AI student performance prediction, with a single-page dashboard UI in HTML/CSS/JS.
- Uses in-memory per-user storage for uploaded/predicted student records, plus a flat JSON file for users.
- ML models are trained or loaded at app startup and used for predictions.
- Supports bulk CSV/XLSX upload, single prediction, reports (PDF/Excel), recommendations, and email alerts.

## Tech Stack

- Backend: Python, Flask, Flask-Cors, pandas, numpy, scikit-learn, joblib
- Reports: reportlab (PDF), xlsxwriter (Excel)
- Frontend: static HTML + CSS + vanilla JS, Chart.js for charts
- Auth storage: users.json with bcrypt password hashes

## Runtime and Entry Point

- app.py is the Flask entry point. It seeds a default admin and initializes ML models on startup.
- Models are loaded from models/ if present; otherwise a synthetic dataset is generated and models are trained and saved.

## Data Storage and State

- users.json stores user accounts, roles, grading scheme, and email settings.
- In-memory store keyed by user_id: { students: [...], upload_info: {...} }.
- Data is not persisted across server restarts, except users.json and ML model files.

## Core Backend Modules

### app.py

- Flask routes, in-memory store, and API endpoints.
- Uses StudentPerformancePredictor for scoring and classification.
- Builds per-student records with computed values, risk factors, and recommendations.
- Handles CSV/XLSX upload parsing and validation.

### auth.py

- User CRUD over users.json with bcrypt hashing.
- Seed admin: username CU_Admin, password Admin123! (hashed in file).
- Decorators for login_required and admin_required.
- Default grading scheme and email settings per user.

### ml_models.py

- StudentPerformancePredictor encapsulates:
  - Synthetic dataset generation (beta distributions).
  - Train/test split and model training.
  - Models: RandomForestClassifier (pass/fail, at-risk), GradientBoostingClassifier (grade), RandomForestRegressor (score).
  - StandardScaler for features.
- Scheme-aware final score and grade mapping.
- Predicts:
  - final_score, predicted_score, pass/fail, grade category/confidence
  - at-risk flag + risk probability + risk factors

### recommendations.py

- Rule-based recommendations for at-risk students.
- Produces overall priority and detailed intervention items.

### notifications.py

- Gmail SMTP email alerts with HTML and plain text versions.
- Uses a background thread so HTTP responses are not blocked.
- Sends alerts if at-risk count exceeds a user-defined threshold and notifications are enabled.

### reports.py

- PDF report for individual student with score breakdown and risk factors.
- Excel report for class with summary stats, grade distribution chart, and at-risk list.

## Frontend Structure

### templates/index.html

- Dashboard UI with sidebar tabs:
  - Dashboard
  - Bulk Upload
  - Single Prediction
  - All Students
  - Reports
  - Settings
  - Admin (visible to admin role only)
- Modals:
  - Student detail modal
  - Add lecturer modal
- Toast notification container

### templates/login.html

- Login form and first-login password setup flow.

### static/js/app.js

- Orchestrates UI state, API calls, and rendering.
- Client-side state: allStudents, currentUser, charts.
- Handles:
  - Auth (me, logout)
  - Dashboard stats and charts
  - File upload and validation
  - Single prediction form
  - Students table, filters, detail modal
  - Reports export
  - Settings save/test email
  - Admin management (add, deactivate, reset password)

### static/css/style.css

- Global layout styles, cards, tables, forms, modals, toasts.
- Dedicated sections for login page, admin panel, and recommendation UI.

## API Endpoints (High Level)

### Auth

- GET /login: login page
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me
- POST /api/auth/set-password

### Admin

- GET /api/admin/users
- POST /api/admin/users
- PUT /api/admin/users/<uid>
- POST /api/admin/users/<uid>/deactivate
- POST /api/admin/users/<uid>/reset-password

### Settings

- GET /api/settings
- POST /api/settings/scheme
- POST /api/settings/email
- POST /api/settings/email/test

### Data and Predictions

- POST /api/predict
- POST /api/upload-bulk
- GET /api/dashboard
- GET /api/students
- GET /api/student/<sid>
- POST /api/clear
- GET /api/template

### Exports

- GET /api/export/student/<sid>
- GET /api/export/class

## Student Record Shape (Simplified)

- Input fields: student_name, student_id, attendance, exam_score, test1..N, assignment1..N
- Computed fields:
  - avg_test, avg_assignment, final_score, predicted_score
  - pass_fail, pass_probability
  - grade_category, grade_confidence
  - at_risk, risk_probability, risk_factors
  - recommendation_priority, recommendations

## Validation Rules

- Required base fields: student_name, attendance, exam_score.
- Tests and assignments are determined by the user scheme.
- Numeric scores must be between 0 and 100.

## Known Mismatches / Risks

- app.py calls generate_student_pdf(s, scheme) but reports.py defines generate_student_pdf(student) with a single parameter.
- app.py calls generate_class_excel(students, stats, scheme) but reports.py defines generate_class_excel(students, stats) with two parameters.
- These mismatches will raise runtime errors when exporting reports unless resolved.

## Environment Notes

- users.json currently contains sample admin and lecturer accounts plus SMTP config values.
- Email uses Gmail SMTP with app password (configured per user).
