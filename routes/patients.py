from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Patient
from routes.auth_utils import login_required

patients_bp = Blueprint("patients", __name__, url_prefix="/patients")


@patients_bp.route("/")
@login_required(roles=["admin"])
def list_patients():
    q = request.args.get("q", "").strip()
    query = Patient.query
    if q:
        query = query.filter(Patient.name.ilike(f"%{q}%"))
    patients = query.order_by(Patient.id.desc()).all()
    return render_template("patients/list.html", patients=patients, q=q)


@patients_bp.route("/new", methods=["GET", "POST"])
@login_required(roles=["admin"])
def new_patient():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        if not name:
            errors.append("Patient name is required.")
        if not age.isdigit() or not (0 < int(age) < 130):
            errors.append("Enter a valid age.")
        if not gender:
            errors.append("Gender is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("patients/form.html", patient=None, form=request.form)

        patient = Patient(name=name, age=int(age), gender=gender, phone=phone, address=address)
        db.session.add(patient)
        db.session.commit()
        flash(f"Patient '{name}' registered with ID {patient.id}.", "success")
        return redirect(url_for("patients.list_patients"))

    return render_template("patients/form.html", patient=None, form={})


@patients_bp.route("/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required(roles=["admin"])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        if not name:
            errors.append("Patient name is required.")
        if not age.isdigit() or not (0 < int(age) < 130):
            errors.append("Enter a valid age.")
        if not gender:
            errors.append("Gender is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("patients/form.html", patient=patient, form=request.form)

        patient.name = name
        patient.age = int(age)
        patient.gender = gender
        patient.phone = phone
        patient.address = address
        db.session.commit()
        flash("Patient details updated.", "success")
        return redirect(url_for("patients.list_patients"))

    return render_template("patients/form.html", patient=patient, form=patient.__dict__)


@patients_bp.route("/<int:patient_id>/delete", methods=["POST"])
@login_required(roles=["admin"])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    flash(f"Patient '{patient.name}' and related records removed.", "success")
    return redirect(url_for("patients.list_patients"))


@patients_bp.route("/<int:patient_id>")
@login_required(roles=["admin"])
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    return render_template("patients/view.html", patient=patient)
