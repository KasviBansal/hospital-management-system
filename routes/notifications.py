from flask import Blueprint, render_template, jsonify, redirect, url_for
from models import db, Notification
from routes.auth_utils import login_required, get_current_user

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")
notifications_bp.before_request(login_required(roles=["admin", "doctor", "patient", "pharmacy"])(lambda: None))


@notifications_bp.route("/")
def list_notifications():
    user = get_current_user()
    notes = (Notification.query.filter_by(user_id=user.id)
             .order_by(Notification.created_at.desc()).limit(100).all())
    return render_template("notifications/list.html", notifications=notes)


@notifications_bp.route("/api/recent")
def api_recent():
    user = get_current_user()
    notes = (Notification.query.filter_by(user_id=user.id)
             .order_by(Notification.created_at.desc()).limit(8).all())
    unread = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({
        "unread_count": unread,
        "notifications": [{
            "id": n.id, "message": n.message, "category": n.category,
            "url": url_for("notifications.open_notification", note_id=n.id),
            "is_read": n.is_read, "created_at": n.created_at.strftime("%d %b, %H:%M"),
        } for n in notes],
    })


@notifications_bp.route("/<int:note_id>/open")
def open_notification(note_id):
    user = get_current_user()
    note = Notification.query.filter_by(id=note_id, user_id=user.id).first_or_404()
    note.is_read = True
    db.session.commit()
    return redirect(note.link or url_for("notifications.list_notifications"))


@notifications_bp.route("/mark-all-read", methods=["POST"])
def mark_all_read():
    user = get_current_user()
    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})
