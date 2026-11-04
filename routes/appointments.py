from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models import db, Appointment, Patient, Doctor, doctor_is_on_leave, notify
from routes.auth_utils import login_required, get_current_user

appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointments")
appointments_bp.before_request(login_required(roles=["admin", "doctor", "patient"])(lambda: None))


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _has_conflict(doctor_id, appt_date, appt_time, exclude_id=None):
    query = Appointment.query.filter_by(doctor_id=doctor_id, appt_date=appt_date,
                                         appt_time=appt_time, status="Booked")
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)
    return query.first() is not None


def _validate_date_not_past(appt_date, errors):
    """Shared rule: an appointment can never be booked/rescheduled into the past."""
    if appt_date and appt_date < date.today():
        errors.append("You can't book or reschedule an appointment into the past. "
                       "Please choose today or a future date.")


@appointments_bp.route("/")
def list_appointments():
    user = get_current_user()
    status = request.args.get("status", "")
    query = Appointment.query

    if user.role == "doctor":
        query = query.filter_by(doctor_id=user.doctor_profile.id)
    elif user.role == "patient":
        query = query.filter_by(patient_id=user.patient_profile.id)

    if status:
        query = query.filter_by(status=status)
    appts = query.order_by(Appointment.appt_date.desc(), Appointment.appt_time.desc()).all()
    return render_template("appointments/list.html", appointments=appts, status=status, user=user)


@appointments_bp.route("/new", methods=["GET", "POST"])
@login_required(roles=["admin", "patient"])
def new_appointment():
    user = get_current_user()
    patients = Patient.query.order_by(Patient.name).all() if user.role == "admin" else None
    doctors = Doctor.query.order_by(Doctor.name).all()
    own_patient = user.patient_profile if user.role == "patient" else None
    today_str = date.today().isoformat()

    if request.method == "POST":
        patient_id = own_patient.id if own_patient else request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        appt_date = _parse_date(request.form.get("appt_date", ""))
        appt_time = request.form.get("appt_time", "").strip()
        reason = request.form.get("reason", "").strip()

        errors = []
        if not patient_id:
            errors.append("Select a patient.")
        if not doctor_id:
            errors.append("Select a doctor.")
        if not appt_date:
            errors.append("Enter a valid date.")
        if not appt_time:
            errors.append("Enter an appointment time.")

        _validate_date_not_past(appt_date, errors)

        if not errors and doctor_id and appt_date and doctor_is_on_leave(int(doctor_id), appt_date):
            errors.append("This doctor is on approved leave on the selected date. "
                           "Please pick another date or doctor.")

        if not errors and _has_conflict(doctor_id, appt_date, appt_time):
            errors.append("This doctor already has a booked appointment at that date and time. "
                           "Please choose a different slot.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("appointments/form.html", appointment=None, form=request.form,
                                    patients=patients, doctors=doctors, own_patient=own_patient,
                                    today_str=today_str)

        doctor = Doctor.query.get(doctor_id)
        appt = Appointment(patient_id=patient_id, doctor_id=doctor_id, appt_date=appt_date,
                            appt_time=appt_time, reason=reason, status="Booked",
                            fee=doctor.consultation_fee, payment_status="Pending")
        db.session.add(appt)
        db.session.commit()
        flash("Appointment created. Complete payment to confirm your slot.", "success")
        return redirect(url_for("payments.pay", purpose="appointment", reference_id=appt.id))

    return render_template("appointments/form.html", appointment=None, form={}, patients=patients,
                            doctors=doctors, own_patient=own_patient, today_str=today_str)


@appointments_bp.route("/<int:appt_id>/edit", methods=["GET", "POST"])
@login_required(roles=["admin", "patient"])
def edit_appointment(appt_id):
    user = get_current_user()
    appt = Appointment.query.get_or_404(appt_id)
    if user.role == "patient" and appt.patient_id != user.patient_profile.id:
        abort(403)

    patients = Patient.query.order_by(Patient.name).all() if user.role == "admin" else None
    doctors = Doctor.query.order_by(Doctor.name).all()
    own_patient = user.patient_profile if user.role == "patient" else None
    today_str = date.today().isoformat()

    if request.method == "POST":
        patient_id = appt.patient_id if own_patient else request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        appt_date = _parse_date(request.form.get("appt_date", ""))
        appt_time = request.form.get("appt_time", "").strip()
        reason = request.form.get("reason", "").strip()

        errors = []
        if not doctor_id:
            errors.append("Select a doctor.")
        if not appt_date:
            errors.append("Enter a valid date.")
        if not appt_time:
            errors.append("Enter an appointment time.")

        _validate_date_not_past(appt_date, errors)

        if not errors and doctor_id and appt_date and doctor_is_on_leave(int(doctor_id), appt_date):
            errors.append("This doctor is on approved leave on the selected date. "
                           "Please pick another date or doctor.")

        if not errors and _has_conflict(doctor_id, appt_date, appt_time, exclude_id=appt.id):
            errors.append("This doctor already has a booked appointment at that date and time.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("appointments/form.html", appointment=appt, form=request.form,
                                    patients=patients, doctors=doctors, own_patient=own_patient,
                                    today_str=today_str)

        appt.patient_id = patient_id
        appt.doctor_id = doctor_id
        appt.appt_date = appt_date
        appt.appt_time = appt_time
        appt.reason = reason
        db.session.commit()
        flash("Appointment rescheduled.", "success")
        return redirect(url_for("appointments.list_appointments"))

    form = {
        "patient_id": appt.patient_id, "doctor_id": appt.doctor_id,
        "appt_date": appt.appt_date.isoformat(), "appt_time": appt.appt_time, "reason": appt.reason,
    }
    return render_template("appointments/form.html", appointment=appt, form=form, patients=patients,
                            doctors=doctors, own_patient=own_patient, today_str=today_str)


@appointments_bp.route("/<int:appt_id>/cancel", methods=["POST"])
@login_required(roles=["admin", "patient"])
def cancel_appointment(appt_id):
    user = get_current_user()
    appt = Appointment.query.get_or_404(appt_id)
    if user.role == "patient" and appt.patient_id != user.patient_profile.id:
        abort(403)
    appt.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "success")
    return redirect(url_for("appointments.list_appointments"))


@appointments_bp.route("/<int:appt_id>/complete", methods=["POST"])
@login_required(roles=["admin", "doctor"])
def complete_appointment(appt_id):
    user = get_current_user()
    appt = Appointment.query.get_or_404(appt_id)
    if user.role == "doctor" and appt.doctor_id != user.doctor_profile.id:
        abort(403)
    appt.status = "Completed"
    db.session.commit()
    flash("Appointment marked completed. You can now add a medical record for this visit.", "success")
    return redirect(url_for("records.new_record", appointment_id=appt.id))
