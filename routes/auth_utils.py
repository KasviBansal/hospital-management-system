from functools import wraps
from flask import session, redirect, url_for, flash, g
from models import User


def get_current_user():
    if "user_id" not in session:
        return None
    if not hasattr(g, "_current_user"):
        g._current_user = User.query.get(session["user_id"])
    return g._current_user


def login_required(roles=None):
    """Restrict a route to logged-in users, optionally to specific roles.
    roles: list of allowed role strings, e.g. ["admin", "doctor"]."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if user is None:
                flash("Please log in to continue.", "error")
                return redirect(url_for("auth.portal"))
            if roles and user.role not in roles:
                flash("You don't have access to that page.", "error")
                return redirect(url_for("auth.dashboard_redirect"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator


def role_dashboard_endpoint(role):
    return {
        "admin": "auth.admin_dashboard",
        "doctor": "auth.doctor_dashboard",
        "patient": "auth.patient_dashboard",
        "pharmacy": "auth.pharmacy_dashboard",
    }.get(role, "auth.portal")
