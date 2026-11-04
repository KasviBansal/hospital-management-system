from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import (db, DoctorLeave, Appointment, notify, notify_admins,
                     doctor_is_on_leave, next_leave_end)
from routes.auth_utils import login_required, get_current_user

leave_bp = Blueprint("leave", __name__, url_prefix="/leave")
leave_bp.before_request(login_required(roles=["admin", "doctor", "patient"])(lambda: None))


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ---------- Doctor: request + view own leave ----------

@leave_bp.route("/new", methods=["GET", "POST"])
@login_required(roles=["doctor"])
def new_leave():
    doctor = get_current_user().doctor_profile
    today_str = date.today().isoformat()

    if request.method == "POST":
        start_date = _parse_date(request.form.get("start_date", ""))
        end_date = _parse_date(request.form.get("end_date", ""))
        reason = request.form.get("reason", "").strip()

        errors = []
        if not start_date or not end_date:
            errors.append("Enter valid start and end dates.")
        elif start_date < date.today():
            errors.append("Leave can't start in the past. Choose today or a future date.")
        elif end_date < start_date:
            errors.append("End date must be on or after the start date.")
        if not reason:
            errors.append("Please give a reason for the leave request.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("leave/form.html", form=request.form, today_str=today_str)

        db.session.add(DoctorLeave(doctor_id=doctor.id, start_date=start_date, end_date=end_date,
                                    reason=reason, status="Pending"))
        notify_admins(f"Dr. {doctor.name} requested leave from {start_date.strftime('%d %b')} "
                      f"to {end_date.strftime('%d %b %Y')}.", "info", url_for("leave.admin_leaves"))
        db.session.commit()
        flash("Leave request submitted. You'll be notified once admin reviews it.", "success")
        return redirect(url_for("leave.my_leaves"))

    return render_template("leave/form.html", form={}, today_str=today_str)


@leave_bp.route("/my")
@login_required(roles=["doctor"])
def my_leaves():
    leaves = (DoctorLeave.query.filter_by(doctor_id=get_current_user().doctor_profile.id)
              .order_by(DoctorLeave.requested_at.desc()).all())
    return render_template("leave/my_leaves.html", leaves=leaves)


# ---------- Admin: review + decide ----------

@leave_bp.route("/admin")
@login_required(roles=["admin"])
def admin_leaves():
    status = request.args.get("status", "")
    query = DoctorLeave.query
    if status:
        query = query.filter_by(status=status)
    leaves = query.order_by(DoctorLeave.requested_at.desc()).all()
    return render_template("leave/admin_list.html", leaves=leaves, status=status)


@leave_bp.route("/admin/<int:leave_id>/decide", methods=["POST"])
@login_required(roles=["admin"])
def decide_leave(leave_id):
    admin = get_current_user()
    leave = DoctorLeave.query.get_or_404(leave_id)
    decision = request.form.get("decision", "")

    if decision not in ("Approved", "Rejected"):
        flash("Invalid decision.", "error")
        return redirect(url_for("leave.admin_leaves"))

    leave.status = decision
    leave.decided_at = datetime.utcnow()
    leave.decided_by_id = admin.id

    span = f"{leave.start_date.strftime('%d %b')} – {leave.end_date.strftime('%d %b %Y')}"
    doctor_user = leave.doctor.user_account
    if doctor_user:
        notify(doctor_user.id, f"Your leave request ({span}) was {decision.lower()}.",
               "success" if decision == "Approved" else "warning", url_for("leave.my_leaves"))

    flagged = 0
    if decision == "Approved":
        clashing = Appointment.query.filter(
            Appointment.doctor_id == leave.doctor_id, Appointment.status == "Booked",
            Appointment.appt_date >= leave.start_date, Appointment.appt_date <= leave.end_date).all()
        flagged = len(clashing)
        for appt in clashing:
            pu = appt.patient.user_account
            if pu:
                notify(pu.id, f"Dr. {leave.doctor.name} is on leave on "
                              f"{appt.appt_date.strftime('%d %b %Y')}. Please reschedule your appointment.",
                       "alert", url_for("appointments.list_appointments"))

    db.session.commit()
    msg = f"Leave request {decision.lower()}."
    if flagged:
        msg += f" {flagged} existing appointment(s) in that range were flagged to the patients."
    flash(msg, "success")
    return redirect(url_for("leave.admin_leaves"))


# ---------- Availability check (used by the booking form) ----------

@leave_bp.route("/availability/<int:doctor_id>")
def check_availability(doctor_id):
    on_date = _parse_date(request.args.get("date", ""))
    if not on_date:
        return jsonify({"error": "invalid date"}), 400
    end = next_leave_end(doctor_id, on_date)
    return jsonify({"on_leave": end is not None,
                    "back_on": end.isoformat() if end else None})
