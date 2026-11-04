from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Doctor
from routes.auth_utils import login_required

doctors_bp = Blueprint("doctors", __name__, url_prefix="/doctors")


@doctors_bp.route("/")
@login_required(roles=["admin"])
def list_doctors():
    q = request.args.get("q", "").strip()
    query = Doctor.query
    if q:
        query = query.filter(Doctor.name.ilike(f"%{q}%") | Doctor.specialization.ilike(f"%{q}%"))
    doctors = query.order_by(Doctor.id.desc()).all()
    return render_template("doctors/list.html", doctors=doctors, q=q)


@doctors_bp.route("/new", methods=["GET", "POST"])
@login_required(roles=["admin"])
def new_doctor():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()
        available_days = request.form.get("available_days", "").strip()
        available_time = request.form.get("available_time", "").strip()

        errors = []
        if not name:
            errors.append("Doctor name is required.")
        if not specialization:
            errors.append("Specialization is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("doctors/form.html", doctor=None, form=request.form)

        doctor = Doctor(name=name, specialization=specialization, phone=phone,
                         available_days=available_days, available_time=available_time)
        db.session.add(doctor)
        db.session.commit()
        flash(f"Dr. {name} added.", "success")
        return redirect(url_for("doctors.list_doctors"))

    return render_template("doctors/form.html", doctor=None, form={})


@doctors_bp.route("/<int:doctor_id>/edit", methods=["GET", "POST"])
@login_required(roles=["admin"])
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()
        available_days = request.form.get("available_days", "").strip()
        available_time = request.form.get("available_time", "").strip()

        errors = []
        if not name:
            errors.append("Doctor name is required.")
        if not specialization:
            errors.append("Specialization is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("doctors/form.html", doctor=doctor, form=request.form)

        doctor.name = name
        doctor.specialization = specialization
        doctor.phone = phone
        doctor.available_days = available_days
        doctor.available_time = available_time
        db.session.commit()
        flash("Doctor details updated.", "success")
        return redirect(url_for("doctors.list_doctors"))

    return render_template("doctors/form.html", doctor=doctor, form=doctor.__dict__)


@doctors_bp.route("/<int:doctor_id>/delete", methods=["POST"])
@login_required(roles=["admin"])
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash(f"Dr. {doctor.name} removed.", "success")
    return redirect(url_for("doctors.list_doctors"))
