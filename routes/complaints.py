from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
from models import db, Complaint, COMPLAINT_CATEGORIES, notify, notify_admins
from routes.auth_utils import login_required, get_current_user

complaints_bp = Blueprint("complaints", __name__, url_prefix="/complaints")
complaints_bp.before_request(login_required(roles=["admin", "doctor", "patient"])(lambda: None))


@complaints_bp.route("/new", methods=["GET", "POST"])
@login_required(roles=["doctor", "patient"])
def new_complaint():
    user = get_current_user()

    if request.method == "POST":
        category = request.form.get("category", "")
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()

        errors = []
        if category not in COMPLAINT_CATEGORIES:
            errors.append("Select a valid category.")
        if not location:
            errors.append("Enter a location (e.g. Room 204, Ward 3, OPD corridor).")
        if not description:
            errors.append("Describe the issue.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("complaints/form.html", categories=COMPLAINT_CATEGORIES, form=request.form)

        db.session.add(Complaint(user_id=user.id, category=category, location=location,
                                  description=description, status="Open"))
        notify_admins(f"New {category} complaint at {location} from {user.name}.",
                      "alert", url_for("complaints.admin_complaints"))
        db.session.commit()
        flash("Complaint submitted. Admin has been notified.", "success")
        return redirect(url_for("complaints.my_complaints"))

    return render_template("complaints/form.html", categories=COMPLAINT_CATEGORIES, form={})


@complaints_bp.route("/my")
@login_required(roles=["doctor", "patient"])
def my_complaints():
    user = get_current_user()
    complaints = Complaint.query.filter_by(user_id=user.id).order_by(Complaint.created_at.desc()).all()
    return render_template("complaints/my_complaints.html", complaints=complaints)


# ---------- Admin ----------

@complaints_bp.route("/admin")
@login_required(roles=["admin"])
def admin_complaints():
    status = request.args.get("status", "")
    query = Complaint.query
    if status:
        query = query.filter_by(status=status)
    complaints = query.order_by(Complaint.created_at.desc()).all()
    return render_template("complaints/admin_list.html", complaints=complaints, status=status)


@complaints_bp.route("/admin/<int:complaint_id>/status", methods=["POST"])
@login_required(roles=["admin"])
def admin_update_status(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    new_status = request.form.get("status", "")
    if new_status in ["Open", "In Progress", "Resolved"]:
        complaint.status = new_status
        complaint.resolved_at = datetime.utcnow() if new_status == "Resolved" else None
        notify(complaint.user_id, f"Your {complaint.category} complaint ({complaint.location}) is now "
                                  f"{new_status.lower()}.",
               "success" if new_status == "Resolved" else "info", url_for("complaints.my_complaints"))
        db.session.commit()
        flash(f"Complaint #{complaint.id} marked as {new_status}.", "success")
    return redirect(url_for("complaints.admin_complaints"))
