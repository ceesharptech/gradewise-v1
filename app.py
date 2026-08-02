import os, io, json
from datetime import datetime
from flask import (Flask, render_template, request, jsonify,
                   send_file, session, redirect, url_for)
from flask_cors import CORS
import pandas as pd
import numpy as np

from ml_models        import StudentPerformancePredictor
from reports          import generate_student_pdf, generate_class_excel
from auth             import (seed_admin, authenticate, login_user, logout_user,
                               current_user, is_logged_in, is_admin,
                               login_required, admin_required,
                               get_all_users, get_user_by_id,
                               create_lecturer, update_user, set_password,
                               save_scheme, save_email_settings,
                               deactivate_user, safe_user, DEFAULT_SCHEME)
from recommendations  import generate as gen_recs
from notifications    import send_at_risk_alert, send_test_email

app = Flask(__name__)
app.secret_key = "spps-secret-key-2024"
CORS(app)

# ── In-memory store (per-user keyed by user_id) ─────────────
# store[uid] = { 'students': [...], 'upload_info': {...} }
store: dict[int, dict] = {}

def get_store(uid: int) -> dict:
    if uid not in store:
        store[uid] = {"students": [], "upload_info": None}
    return store[uid]

# ── ML predictor ─────────────────────────────────────────────
predictor = StudentPerformancePredictor()

def init_predictor():
    if predictor.models_exist():
        predictor.load_models()
        print("✓ Models loaded.")
    else:
        print("Training models — please wait...")
        df = predictor.generate_dataset(500)
        predictor.train_models(df)
        predictor.save_models()
        print("✓ Models trained and saved.")

# ── Schema helpers ───────────────────────────────────────────
REQUIRED_BASE = ["student_name", "attendance", "exam_score"]

def scheme_for(uid: int) -> dict:
    u = get_user_by_id(uid)
    return u.get("scheme", DEFAULT_SCHEME) if u else DEFAULT_SCHEME

def required_cols(scheme: dict) -> list:
    nt = scheme.get("num_tests", 3)
    na = scheme.get("num_assignments", 3)
    tests   = [f"test{i+1}"       for i in range(nt)]
    assigns = [f"assignment{i+1}" for i in range(na)]
    return REQUIRED_BASE + tests + assigns

def validate_row(row, idx: int, scheme: dict) -> list:
    errors = []
    for col in required_cols(scheme):
        if col == "student_name":
            if not str(row.get("student_name", "")).strip():
                errors.append(f"Row {idx}: 'student_name' is empty")
        else:
            try:
                val = float(row[col])
                if not (0 <= val <= 100):
                    errors.append(f"Row {idx}: '{col}' must be 0-100 (got {val})")
            except (ValueError, TypeError):
                errors.append(f"Row {idx}: '{col}' is not a valid number")
    return errors

def build_record(sid: int, row, pred: dict, recs: dict) -> dict:
    scheme = scheme_for(session.get("user_id", 0))
    nt = scheme.get("num_tests", 3)
    na = scheme.get("num_assignments", 3)

    base = {
        "id":             sid,
        "student_id":     str(row.get("student_id", f"STU{sid:04d}")),
        "name":           str(row.get("student_name", "")).strip(),
        "attendance":     round(float(row.get("attendance", 0)), 2),
        "exam_score":     round(float(row.get("exam_score",  0)), 2),
        "avg_test":       pred["avg_test"],
        "avg_assignment": pred["avg_assignment"],
        "final_score":    pred["final_score"],
        "predicted_score":pred["predicted_score"],
        "pass_fail":      pred["pass_fail"],
        "pass_probability":pred["pass_probability"],
        "grade_category": pred["grade_category"],
        "grade_confidence":pred["grade_confidence"],
        "at_risk":        pred["at_risk"],
        "risk_probability":pred["risk_probability"],
        "risk_factors":   pred["risk_factors"],
        "recommendation_priority": recs["priority"],
        "recommendations":         recs["recommendations"],
    }
    for i in range(nt):
        base[f"test{i+1}"] = round(float(row.get(f"test{i+1}", 0)), 2)
    for i in range(na):
        base[f"assignment{i+1}"] = round(float(row.get(f"assignment{i+1}", 0)), 2)
    return base

def compute_stats(students: list) -> dict:
    if not students:
        return {}
    scores   = [s["final_score"] for s in students]
    at_risk  = sum(1 for s in students if s["at_risk"] == "Yes")
    passed   = sum(1 for s in students if s["pass_fail"] == "Pass")
    grade_dist = {}
    for s in students:
        g = s["grade_category"]
        grade_dist[g] = grade_dist.get(g, 0) + 1
    priority_dist = {}
    for s in students:
        p = s.get("recommendation_priority", "NONE")
        priority_dist[p] = priority_dist.get(p, 0) + 1
    return {
        "total_students":   len(students),
        "pass_count":       passed,
        "fail_count":       len(students) - passed,
        "pass_rate":        round(passed / len(students) * 100, 1),
        "at_risk_count":    at_risk,
        "average_score":    round(sum(scores) / len(scores), 2),
        "highest_score":    round(max(scores), 2),
        "lowest_score":     round(min(scores), 2),
        "grade_distribution":    grade_dist,
        "priority_distribution": priority_dist,
    }

# ════════════════════════════════════════════════════════════
# AUTH ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET"])
def login_page():
    if is_logged_in():
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    d        = request.json or {}
    username = d.get("username", "").strip()
    password = d.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = authenticate(username, password)
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user)
    return jsonify({
        "message":       "Login successful",
        "user":          safe_user(user),
        "must_change_pw": user.get("must_change_pw", False),
    })

@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    logout_user()
    return jsonify({"message": "Logged out"})

@app.route("/api/auth/me", methods=["GET"])
@login_required
def api_me():
    u = current_user()
    return jsonify(safe_user(u)) if u else jsonify({"error": "Not found"}), 404

@app.route("/api/auth/set-password", methods=["POST"])
@login_required
def api_set_password():
    d   = request.json or {}
    pw  = d.get("password", "")
    if len(pw) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    set_password(session["user_id"], pw)
    return jsonify({"message": "Password updated"})

# ════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_list_users():
    users = [safe_user(u) for u in get_all_users() if u["role"] != "admin"]
    return jsonify(users)

@app.route("/api/admin/users", methods=["POST"])
@admin_required
def admin_create_user():
    d = request.json or {}
    try:
        user = create_lecturer(
            full_name = d.get("full_name", "").strip(),
            username  = d.get("username",  "").strip(),
            email     = d.get("email",     "").strip(),
            password  = d.get("password",  ""),
        )
        return jsonify(safe_user(user)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/admin/users/<int:uid>", methods=["PUT"])
@admin_required
def admin_update_user(uid):
    d = request.json or {}
    allowed = {"full_name", "email", "active"}
    updates = {k: v for k, v in d.items() if k in allowed}
    try:
        updated = update_user(uid, updates)
        return jsonify(safe_user(updated))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@app.route("/api/admin/users/<int:uid>/deactivate", methods=["POST"])
@admin_required
def admin_deactivate(uid):
    try:
        deactivate_user(uid)
        return jsonify({"message": "User deactivated"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@app.route("/api/admin/users/<int:uid>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(uid):
    """Mark account as must_change_pw so lecturer sets it on next login."""
    try:
        update_user(uid, {"must_change_pw": True, "password_hash": ""})
        return jsonify({"message": "Password reset — lecturer must set a new password on next login"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

# ════════════════════════════════════════════════════════════
# SETTINGS ROUTES
# ════════════════════════════════════════════════════════════

@app.route("/api/settings", methods=["GET"])
@login_required
def get_settings():
    u = current_user()
    return jsonify({
        "scheme":         u.get("scheme", DEFAULT_SCHEME),
        "email_settings": {
            k: v for k, v in u.get("email_settings", {}).items()
            if k != "sender_password"          # never send password to client
        }
    })

@app.route("/api/settings/scheme", methods=["POST"])
@login_required
def update_scheme():
    d = request.json or {}
    scheme = d.get("scheme")
    if not scheme:
        return jsonify({"error": "No scheme provided"}), 400

    # Validate weights sum to 100
    w = scheme.get("weights", {})
    total = sum(w.get(k, 0) for k in ("exam","tests","assignments","attendance"))
    if abs(total - 100) > 0.01:
        return jsonify({"error": f"Weights must sum to 100 (got {total})"}), 400

    save_scheme(session["user_id"], scheme)
    return jsonify({"message": "Grading scheme saved", "scheme": scheme})

@app.route("/api/settings/email", methods=["POST"])
@login_required
def update_email_settings():
    d = request.json or {}
    es = d.get("email_settings", {})

    # Preserve existing password if not re-sent
    u = current_user()
    existing = u.get("email_settings", {})
    if not es.get("sender_password"):
        es["sender_password"] = existing.get("sender_password", "")

    save_email_settings(session["user_id"], es)
    return jsonify({"message": "Email settings saved"})

@app.route("/api/settings/email/test", methods=["POST"])
@login_required
def test_email():
    u  = current_user()
    es = u.get("email_settings", {})
    if not es.get("sender_email") or not es.get("recipient_email"):
        return jsonify({"error": "Sender and recipient email addresses are required"}), 400
    ok, msg = send_test_email(es)
    if ok:
        return jsonify({"message": msg})
    return jsonify({"error": msg}), 500

# ════════════════════════════════════════════════════════════
# PAGES
# ════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def index():
    return render_template("index.html")

# ════════════════════════════════════════════════════════════
# PREDICTION API
# ════════════════════════════════════════════════════════════

@app.route("/api/predict", methods=["POST"])
@login_required
def predict():
    uid    = session["user_id"]
    scheme = scheme_for(uid)
    data   = request.json or {}

    row = {**data, "student_name": data.get("name", "Student")}
    errors = validate_row(row, 1, scheme)
    if errors:
        return jsonify({"error": errors}), 400

    try:
        pred   = predictor.predict_student(data, scheme)
        recs   = gen_recs({**data, **pred}, scheme)
        sid    = len(get_store(uid)["students"]) + 1
        record = build_record(sid, row, pred, recs)
        get_store(uid)["students"].append(record)

        # Notification check (single prediction — threshold still applies)
        u  = get_user_by_id(uid)
        es = u.get("email_settings", {})
        at_risk_all = [s for s in get_store(uid)["students"] if s["at_risk"] == "Yes"]
        send_at_risk_alert(es, u["full_name"], at_risk_all,
                           len(get_store(uid)["students"]), source="prediction")

        return jsonify(record)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/upload-bulk", methods=["POST"])
@login_required
def upload_bulk():
    uid    = session["user_id"]
    scheme = scheme_for(uid)

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f     = request.files["file"]
    fname = f.filename.lower()

    try:
        df = pd.read_csv(f) if fname.endswith(".csv") else pd.read_excel(f)
    except Exception as e:
        return jsonify({"error": f"Could not read file: {e}"}), 400

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing    = [c for c in required_cols(scheme) if c not in df.columns]
    if missing:
        return jsonify({"error": f"Missing columns: {missing}"}), 400

    all_errors = []
    for i, row in df.iterrows():
        all_errors.extend(validate_row(row, i + 2, scheme))
    if all_errors:
        return jsonify({"errors": all_errors, "message": "Validation failed"}), 422

    get_store(uid)["students"] = []
    results = []
    for i, row in df.iterrows():
        try:
            pred   = predictor.predict_student(row.to_dict(), scheme)
            recs   = gen_recs({**row.to_dict(), **pred}, scheme)
            record = build_record(i + 1, row, pred, recs)
            get_store(uid)["students"].append(record)
            results.append(record)
        except Exception as e:
            all_errors.append(f"Row {i+2} ({row.get('student_name','?')}): {e}")

    info = {
        "filename":    f.filename,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total":       len(df),
        "successful":  len(results),
        "failed":      len(all_errors),
    }
    get_store(uid)["upload_info"] = info
    stats = compute_stats(get_store(uid)["students"])

    # Email notification
    u  = get_user_by_id(uid)
    es = u.get("email_settings", {})
    at_risk_list = [s for s in results if s["at_risk"] == "Yes"]
    send_at_risk_alert(es, u["full_name"], at_risk_list, len(results), source="upload")

    return jsonify({
        "message":     f"Processed {len(results)} of {len(df)} records",
        "upload_info": info,
        "stats":       stats,
        "errors":      all_errors,
    })

@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard():
    uid = session["user_id"]
    s   = get_store(uid)
    return jsonify({"stats": compute_stats(s["students"]), "upload_info": s["upload_info"]})

@app.route("/api/students", methods=["GET"])
@login_required
def get_students():
    return jsonify(get_store(session["user_id"])["students"])

@app.route("/api/student/<int:sid>", methods=["GET"])
@login_required
def get_student(sid):
    s = next((x for x in get_store(session["user_id"])["students"] if x["id"] == sid), None)
    return jsonify(s) if s else (jsonify({"error": "Student not found"}), 404)

@app.route("/api/clear", methods=["POST"])
@login_required
def clear_data():
    uid = session["user_id"]
    store[uid] = {"students": [], "upload_info": None}
    return jsonify({"message": "Data cleared"})

@app.route("/api/template", methods=["GET"])
@login_required
def download_template():
    uid    = session["user_id"]
    scheme = scheme_for(uid)
    nt     = scheme.get("num_tests", 3)
    na     = scheme.get("num_assignments", 3)

    cols = {"student_id": ["2023001","2023002"], "student_name": ["John Doe","Jane Smith"],
            "attendance": [85.0, 92.0]}
    for i in range(nt):   cols[f"test{i+1}"]       = [round(70+i*5, 1), round(85+i*3, 1)]
    for i in range(na):   cols[f"assignment{i+1}"]  = [round(80+i*4, 1), round(88+i*2, 1)]
    cols["exam_score"] = [78.0, 91.0]

    buf = io.BytesIO()
    pd.DataFrame(cols).to_csv(buf, index=False)
    buf.seek(0)
    return send_file(buf, mimetype="text/csv", as_attachment=True,
                     download_name="student_template.csv")

@app.route("/api/export/student/<int:sid>", methods=["GET"])
@login_required
def export_student_pdf(sid):
    s      = next((x for x in get_store(session["user_id"])["students"] if x["id"] == sid), None)
    scheme = scheme_for(session["user_id"])
    if not s:
        return jsonify({"error": "Student not found"}), 404
    try:
        buf = generate_student_pdf(s, scheme)
        return send_file(buf, mimetype="application/pdf", as_attachment=True,
                         download_name=f"report_{s['name'].replace(' ','_')}.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/class", methods=["GET"])
@login_required
def export_class_excel_route():
    uid      = session["user_id"]
    students = get_store(uid)["students"]
    scheme   = scheme_for(uid)
    if not students:
        return jsonify({"error": "No data to export"}), 404
    try:
        buf = generate_class_excel(students, compute_stats(students), scheme)
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True, download_name=f"class_report_{ts}.xlsx")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    seed_admin()
    init_predictor()
    app.run(debug=True, host="0.0.0.0", port=5000)