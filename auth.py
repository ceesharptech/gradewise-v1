"""
auth.py  —  User management, password hashing, session helpers
Storage  :  users.json (flat file, no database)
"""
import json, os, bcrypt
from datetime import datetime
from functools import wraps
from flask import session, jsonify, redirect, url_for

USERS_FILE = "users.json"

# ─────────────────────────────────────────────────────────────
# DEFAULT GRADING SCHEME  (Nigerian standard)
# ─────────────────────────────────────────────────────────────
DEFAULT_SCHEME = {
    "num_tests":       3,
    "num_assignments": 3,
    "weights": {
        "exam":        60,
        "tests":       20,
        "assignments": 10,
        "attendance":  10
    },
    "grade_boundaries": {"A": 70, "B": 60, "C": 50, "D": 45},
    "pass_mark": 45
}

DEFAULT_EMAIL_SETTINGS = {
    "notifications_enabled": False,
    "recipient_email":       "",
    "smtp_server":           "smtp.gmail.com",
    "smtp_port":             587,
    "sender_email":          "",
    "sender_password":       "",
    "threshold":             10
}

# ─────────────────────────────────────────────────────────────
# FILE HELPERS
# ─────────────────────────────────────────────────────────────
def _load() -> dict:
    if not os.path.exists(USERS_FILE):
        return {"users": []}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def _save(data: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─────────────────────────────────────────────────────────────
# SEED  (called once on app start)
# ─────────────────────────────────────────────────────────────
def seed_admin():
    """Create the default admin account if it doesn't exist."""
    data = _load()
    if any(u["username"] == "CU_Admin" for u in data["users"]):
        return
    data["users"].append({
        "id":             1,
        "username":       "CU_Admin",
        "password_hash":  _hash("Admin123!"),
        "role":           "admin",
        "full_name":      "System Admin",
        "email":          "admin@spps.com",
        "active":         True,
        "must_change_pw": False,
        "created_at":     datetime.now().isoformat(),
        "scheme":         DEFAULT_SCHEME,
        "email_settings": DEFAULT_EMAIL_SETTINGS
    })
    _save(data)
    print("✓ Admin account seeded (CU_Admin)")

# ─────────────────────────────────────────────────────────────
# PASSWORD
# ─────────────────────────────────────────────────────────────
def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def _verify(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# ─────────────────────────────────────────────────────────────
# USER CRUD
# ─────────────────────────────────────────────────────────────
def get_all_users() -> list:
    return _load()["users"]

def get_user_by_id(uid: int) -> dict | None:
    return next((u for u in _load()["users"] if u["id"] == uid), None)

def get_user_by_username(username: str) -> dict | None:
    return next((u for u in _load()["users"] if u["username"] == username), None)

def authenticate(username: str, password: str) -> dict | None:
    u = get_user_by_username(username)
    if u and u.get("active") and _verify(password, u["password_hash"]):
        return u
    return None

def create_lecturer(full_name: str, username: str, email: str) -> dict:
    data = _load()
    if any(u["username"] == username for u in data["users"]):
        raise ValueError(f"Username '{username}' already exists")
    new_id = max((u["id"] for u in data["users"]), default=0) + 1
    user = {
        "id":             new_id,
        "username":       username,
        "password_hash":  "",          # set on first login
        "role":           "lecturer",
        "full_name":      full_name,
        "email":          email,
        "active":         True,
        "must_change_pw": True,        # forces password set on first login
        "created_at":     datetime.now().isoformat(),
        "scheme":         DEFAULT_SCHEME,
        "email_settings": DEFAULT_EMAIL_SETTINGS
    }
    data["users"].append(user)
    _save(data)
    return user

def update_user(uid: int, updates: dict) -> dict:
    data = _load()
    for u in data["users"]:
        if u["id"] == uid:
            u.update(updates)
            _save(data)
            return u
    raise ValueError("User not found")

def set_password(uid: int, new_password: str):
    update_user(uid, {
        "password_hash":  _hash(new_password),
        "must_change_pw": False
    })

def save_scheme(uid: int, scheme: dict):
    update_user(uid, {"scheme": scheme})

def save_email_settings(uid: int, settings: dict):
    update_user(uid, {"email_settings": settings})

def deactivate_user(uid: int):
    update_user(uid, {"active": False})

def safe_user(u: dict) -> dict:
    """Return user dict without the password hash."""
    return {k: v for k, v in u.items() if k != "password_hash"}

# ─────────────────────────────────────────────────────────────
# SESSION HELPERS
# ─────────────────────────────────────────────────────────────
def login_user(user: dict):
    session["user_id"]   = user["id"]
    session["username"]  = user["username"]
    session["role"]      = user["role"]
    session["full_name"] = user["full_name"]

def logout_user():
    session.clear()

def current_user() -> dict | None:
    uid = session.get("user_id")
    return get_user_by_id(uid) if uid else None

def is_logged_in() -> bool:
    return "user_id" in session

def is_admin() -> bool:
    return session.get("role") == "admin"

# ─────────────────────────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            if _is_api():
                return jsonify({"error": "Unauthorized", "redirect": "/login"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            if _is_api():
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login_page"))
        if not is_admin():
            if _is_api():
                return jsonify({"error": "Forbidden — Admin only"}), 403
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

def _is_api() -> bool:
    from flask import request
    return request.path.startswith("/api/")