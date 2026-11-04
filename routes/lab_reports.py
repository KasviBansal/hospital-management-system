import os
import uuid
from datetime import date
from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   send_file, abort, current_app)
from werkzeug.utils import secure_filename
from models import db, LabReport, Patient, MedicalRecord, notify
from routes.auth_utils import login_required, get_current_user

lab_reports_bp = Blueprint("lab_reports", __name__, url_prefix="/lab-reports")
lab_reports_bp.before_request(login_required(roles=["admin", "doctor", "patient"])(lambda: None))

ALLOWED_EXT = {"pdf": "pdf", "png": "image", "jpg": "image", "jpeg": "image"}
MAGIC = {"pdf": [b"%PDF"], "png": [b"\x89PNG"], "jpg": [b"\xff\xd8\xff"], "jpeg": [b"\xff\xd8\xff"]}
MAX_TEXT_CHARS = 6000


def _ext(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _can_access(user, report):
    if user.role == "admin":
        return True
    if user.role == "patient":
        return report.patient_id == user.patient_profile.id
    if user.role == "doctor":  # only doctors who have treated this patient
        return MedicalRecord.query.filter_by(patient_id=report.patient_id,
                                              doctor_id=user.doctor_profile.id).first() is not None
    return False


def _extract_pdf_text(filepath):
    try:
        from pypdf import PdfReader
        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(filepath).pages).strip()
        if len(text) > MAX_TEXT_CHARS:
            text = text[:MAX_TEXT_CHARS] + "\n\n[truncated]"
        return text or None
    except Exception:
        return None


def _save_upload(file_storage, patient_id):
    ext = _ext(file_storage.filename)
    if ext not in ALLOWED_EXT:
        return None, None, "Only PDF, PNG, or JPG files are allowed."
    head = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    if not any(head.startswith(m) for m in MAGIC[ext]):
        return None, None, "That file's contents don't match its extension. Please upload a real PDF/PNG/JPG."
    folder = current_app.config["LAB_REPORTS_DIR"]
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, f"{patient_id}_{uuid.uuid4().hex}.{ext}")
    file_storage.save(full_path)
    return full_path, ALLOWED_EXT[ext], None


@lab_reports_bp.route("/")
def list_reports():
    user = get_current_user()
    if user.role == "patient":
        reports = (LabReport.query.filter_by(patient_id=user.patient_profile.id)
                   .order_by(LabReport.report_date.desc(), LabReport.id.desc()).all())
        return render_template("lab_reports/patient_list.html", reports=reports, user=user)
    if user.role == "doctor":
        ids = [r.patient_id for r in MedicalRecord.query.filter_by(doctor_id=user.doctor_profile.id).all()]
        reports = (LabReport.query.filter(LabReport.patient_id.in_(ids))
                   .order_by(LabReport.report_date.desc()).all()) if ids else []
        return render_template("lab_reports/doctor_list.html", reports=reports, user=user)
    reports = LabReport.query.order_by(LabReport.report_date.desc(), LabReport.id.desc()).all()
    return render_template("lab_reports/admin_list.html", reports=reports, user=user)


@lab_reports_bp.route("/upload", methods=["GET", "POST"])
@login_required(roles=["patient", "admin"])
def upload_report():
    user = get_current_user()
    patients = Patient.query.order_by(Patient.name).all() if user.role == "admin" else None
    own_patient = user.patient_profile if user.role == "patient" else None
    today_str = date.today().isoformat()

    def render(form):
        return render_template("lab_reports/upload_form.html", patients=patients,
                                own_patient=own_patient, today_str=today_str, form=form)

    if request.method == "POST":
        patient_id = own_patient.id if own_patient else request.form.get("patient_id")
        test_name = request.form.get("test_name", "").strip()
        rdate_raw = request.form.get("report_date", "")
        notes = request.form.get("notes", "").strip()
        file = request.files.get("file")

        errors = []
        if not patient_id:
            errors.append("Select a patient.")
        if not test_name:
            errors.append("Enter the test/report name.")
        if not file or not file.filename:
            errors.append("Choose a PDF or image file to upload.")
        try:
            rdate = date.fromisoformat(rdate_raw) if rdate_raw else date.today()
            if rdate > date.today():
                errors.append("Report date can't be in the future.")
        except ValueError:
            errors.append("Enter a valid report date.")
            rdate = date.today()
        if errors:
            for e in errors:
                flash(e, "error")
            return render(request.form)

        full_path, file_type, err = _save_upload(file, patient_id)
        if err:
            flash(err, "error")
            return render(request.form)

        extracted = _extract_pdf_text(full_path) if file_type == "pdf" else None
        source = "Patient Upload" if own_patient else "Hospital Lab"
        db.session.add(LabReport(patient_id=patient_id, uploaded_by_id=user.id, test_name=test_name,
                                  report_date=rdate, source=source, file_path=full_path,
                                  file_type=file_type, original_filename=secure_filename(file.filename),
                                  extracted_text=extracted, notes=notes))
        if source == "Hospital Lab":
            pu = Patient.query.get(patient_id).user_account
            if pu:
                notify(pu.id, f"Your lab report '{test_name}' is ready.", "success",
                       url_for("lab_reports.list_reports"))
        db.session.commit()
        flash("Lab report saved." + (" Text was read from the PDF." if extracted else ""), "success")
        return redirect(url_for("lab_reports.list_reports"))

    return render({})


@lab_reports_bp.route("/<int:report_id>")
def view_report(report_id):
    report = LabReport.query.get_or_404(report_id)
    if not _can_access(get_current_user(), report):
        abort(403)
    return render_template("lab_reports/view.html", report=report)


@lab_reports_bp.route("/<int:report_id>/file")
def download_file(report_id):
    report = LabReport.query.get_or_404(report_id)
    if not _can_access(get_current_user(), report):
        abort(403)
    if not os.path.exists(report.file_path):
        abort(404)
    return send_file(report.file_path, download_name=report.original_filename or "report")


@lab_reports_bp.route("/<int:report_id>/delete", methods=["POST"])
@login_required(roles=["admin"])
def delete_report(report_id):
    report = LabReport.query.get_or_404(report_id)
    try:
        os.remove(report.file_path)
    except OSError:
        pass
    db.session.delete(report)
    db.session.commit()
    flash("Lab report removed.", "success")
    return redirect(url_for("lab_reports.list_reports"))
