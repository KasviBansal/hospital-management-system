from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models import db, MedicalRecord, Patient, Doctor, Appointment, Prescription, PrescriptionItem, Medicine
from routes.auth_utils import login_required, get_current_user

records_bp = Blueprint("records", __name__, url_prefix="/records")
records_bp.before_request(login_required(roles=["admin", "doctor", "patient"])(lambda: None))


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _can_view(user, record):
    if user.role == "admin":
        return True
    if user.role == "doctor":
        return record.doctor_id == user.doctor_profile.id
    if user.role == "patient":
        return record.patient_id == user.patient_profile.id
    return False


@records_bp.route("/")
def list_records():
    user = get_current_user()
    q = request.args.get("q", "").strip()
    query = MedicalRecord.query.join(Patient)

    if user.role == "doctor":
        query = query.filter(MedicalRecord.doctor_id == user.doctor_profile.id)
    elif user.role == "patient":
        query = query.filter(MedicalRecord.patient_id == user.patient_profile.id)

    if q:
        query = query.filter(Patient.name.ilike(f"%{q}%"))
    records = query.order_by(MedicalRecord.id.desc()).all()
    return render_template("records/list.html", records=records, q=q, user=user)


@records_bp.route("/new", methods=["GET", "POST"])
@login_required(roles=["admin", "doctor"])
def new_record():
    user = get_current_user()
    appointment_id = request.args.get("appointment_id", type=int) or request.form.get("appointment_id", type=int)
    patients = Patient.query.order_by(Patient.name).all()
    doctors = Doctor.query.order_by(Doctor.name).all()
    linked_appt = Appointment.query.get(appointment_id) if appointment_id else None
    own_doctor = user.doctor_profile if user.role == "doctor" else None

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = own_doctor.id if own_doctor else request.form.get("doctor_id")
        diagnosis = request.form.get("diagnosis", "").strip()
        treatment = request.form.get("treatment", "").strip()
        record_date = _parse_date(request.form.get("record_date", "")) or date.today()

        errors = []
        if not patient_id:
            errors.append("Select a patient.")
        if not doctor_id:
            errors.append("Select a doctor.")
        if not diagnosis:
            errors.append("Diagnosis is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("records/form.html", record=None, form=request.form,
                                    patients=patients, doctors=doctors, linked_appt=linked_appt,
                                    own_doctor=own_doctor)

        record = MedicalRecord(patient_id=patient_id, doctor_id=doctor_id, diagnosis=diagnosis,
                                treatment=treatment, record_date=record_date,
                                appointment_id=linked_appt.id if linked_appt else None)
        db.session.add(record)
        from models import notify
        pu = Patient.query.get(patient_id).user_account
        if pu:
            notify(pu.id, "A new medical record was added to your profile.", "info", url_for("records.list_records"))
        db.session.commit()
        flash("Medical record saved.", "success")
        return redirect(url_for("records.view_record", record_id=record.id))

    form = {}
    if linked_appt:
        form = {"patient_id": linked_appt.patient_id, "doctor_id": linked_appt.doctor_id}
    return render_template("records/form.html", record=None, form=form, patients=patients,
                            doctors=doctors, linked_appt=linked_appt, own_doctor=own_doctor)


@records_bp.route("/<int:record_id>")
def view_record(record_id):
    user = get_current_user()
    record = MedicalRecord.query.get_or_404(record_id)
    if not _can_view(user, record):
        abort(403)
    return render_template("records/view.html", record=record, user=user)


@records_bp.route("/<int:record_id>/edit", methods=["GET", "POST"])
@login_required(roles=["admin", "doctor"])
def edit_record(record_id):
    user = get_current_user()
    record = MedicalRecord.query.get_or_404(record_id)
    if user.role == "doctor" and record.doctor_id != user.doctor_profile.id:
        abort(403)
    patients = Patient.query.order_by(Patient.name).all()
    doctors = Doctor.query.order_by(Doctor.name).all()

    if request.method == "POST":
        diagnosis = request.form.get("diagnosis", "").strip()
        treatment = request.form.get("treatment", "").strip()
        record_date = _parse_date(request.form.get("record_date", "")) or record.record_date

        if not diagnosis:
            flash("Diagnosis is required.", "error")
            return render_template("records/form.html", record=record, form=request.form,
                                    patients=patients, doctors=doctors, linked_appt=None, own_doctor=None)

        record.diagnosis = diagnosis
        record.treatment = treatment
        record.record_date = record_date
        db.session.commit()
        flash("Medical record updated.", "success")
        return redirect(url_for("records.view_record", record_id=record.id))

    form = {"diagnosis": record.diagnosis, "treatment": record.treatment,
            "record_date": record.record_date.isoformat(), "patient_id": record.patient_id,
            "doctor_id": record.doctor_id}
    return render_template("records/form.html", record=record, form=form, patients=patients,
                            doctors=doctors, linked_appt=None, own_doctor=None)


@records_bp.route("/<int:record_id>/delete", methods=["POST"])
@login_required(roles=["admin", "doctor"])
def delete_record(record_id):
    user = get_current_user()
    record = MedicalRecord.query.get_or_404(record_id)
    if user.role == "doctor" and record.doctor_id != user.doctor_profile.id:
        abort(403)
    db.session.delete(record)
    db.session.commit()
    flash("Medical record deleted.", "success")
    return redirect(url_for("records.list_records"))


# ---------- Prescriptions (linked to a medical record) ----------

@records_bp.route("/<int:record_id>/prescriptions/new", methods=["GET", "POST"])
@login_required(roles=["admin", "doctor"])
def new_prescription(record_id):
    user = get_current_user()
    record = MedicalRecord.query.get_or_404(record_id)
    if user.role == "doctor" and record.doctor_id != user.doctor_profile.id:
        abort(403)
    medicines = Medicine.query.order_by(Medicine.name).all()

    if request.method == "POST":
        notes = request.form.get("notes", "").strip()
        med_ids = request.form.getlist("medicine_id[]")
        dosages = request.form.getlist("dosage[]")
        quantities = request.form.getlist("quantity[]")

        items = []
        errors = []
        for med_id, dosage, qty in zip(med_ids, dosages, quantities):
            if not med_id or not qty:
                continue
            if not qty.isdigit() or int(qty) <= 0:
                errors.append("Quantity must be a positive number for each medicine.")
                continue
            items.append((med_id, dosage.strip(), int(qty)))

        if not items:
            errors.append("Add at least one medicine to the prescription.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("prescriptions/form.html", record=record, medicines=medicines)

        prescription = Prescription(medical_record_id=record.id, notes=notes, prescribed_date=date.today())
        db.session.add(prescription)
        db.session.flush()

        for med_id, dosage, qty in items:
            db.session.add(PrescriptionItem(prescription_id=prescription.id, medicine_id=med_id,
                                             dosage=dosage, quantity=qty))
        from models import notify
        pu = record.patient.user_account
        if pu:
            notify(pu.id, "A new prescription was added to your record.", "info",
                   url_for("records.view_record", record_id=record.id))
        db.session.commit()
        flash("Prescription created. It is now available in Pharmacy for dispensing.", "success")
        return redirect(url_for("records.view_record", record_id=record.id))

    return render_template("prescriptions/form.html", record=record, medicines=medicines)


@records_bp.route("/prescriptions/<int:prescription_id>")
def view_prescription(prescription_id):
    user = get_current_user()
    prescription = Prescription.query.get_or_404(prescription_id)
    if not _can_view(user, prescription.medical_record):
        abort(403)
    return render_template("prescriptions/view.html", prescription=prescription)
