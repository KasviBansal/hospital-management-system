import calendar as _cal
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import (db, User, Patient, Doctor, Appointment, MedicalRecord, Medicine,
                     Complaint, CafeteriaOrder, DoctorLeave, doctor_is_on_leave, next_leave_end,
                     LOW_STOCK_THRESHOLD, EXPIRY_WARNING_DAYS, ROLES)
from routes.auth_utils import login_required, get_current_user, role_dashboard_endpoint

auth_bp = Blueprint("auth", __name__)


# ---------- Portal / login / signup / logout ----------

@auth_bp.route("/")
def portal():
    if get_current_user():
        return redirect(url_for("auth.dashboard_redirect"))
    return render_template("auth/portal.html")


@auth_bp.route("/about")
def about():
    return render_template("auth/about.html")


@auth_bp.route("/login/<role>", methods=["GET", "POST"])
def login(role):
    if role not in ROLES:
        flash("Unknown login type.", "error")
        return redirect(url_for("auth.portal"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Incorrect email or password.", "error")
            return render_template("auth/login.html", role=role, email=email)

        if user.role != role:
            flash(f"That account is registered as {user.role}, not {role}. "
                  f"Use the {user.role} login instead.", "error")
            return render_template("auth/login.html", role=role, email=email)

        session["user_id"] = user.id
        session["role"] = user.role
        flash(f"Welcome back, {user.name}.", "success")
        return redirect(url_for(role_dashboard_endpoint(user.role)))

    return render_template("auth/login.html", role=role, email="")


@auth_bp.route("/signup/patient", methods=["GET", "POST"])
def signup_patient():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")
        if not email or "@" not in email:
            errors.append("Enter a valid email address.")
        elif User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if not age.isdigit() or not (0 < int(age) < 130):
            errors.append("Enter a valid age.")
        if not gender:
            errors.append("Select a gender.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/signup_patient.html", form=request.form)

        patient = Patient(name=name, age=int(age), gender=gender, phone=phone, address=address)
        db.session.add(patient)
        db.session.flush()

        user = User(name=name, email=email, role="patient", phone=phone, patient_id=patient.id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created. You can now log in.", "success")
        return redirect(url_for("auth.login", role="patient"))

    return render_template("auth/signup_patient.html", form={})


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("auth.portal"))


@auth_bp.route("/dashboard")
@login_required()
def dashboard_redirect():
    user = get_current_user()
    return redirect(url_for(role_dashboard_endpoint(user.role)))


# ---------- Role dashboards ----------

@auth_bp.route("/admin/dashboard")
@login_required(roles=["admin"])
def admin_dashboard():
    today = date.today()
    soon = today + timedelta(days=EXPIRY_WARNING_DAYS)
    stats = {
        "patients": Patient.query.count(),
        "doctors": Doctor.query.count(),
        "appointments_today": Appointment.query.filter_by(appt_date=today, status="Booked").count(),
        "medicines": Medicine.query.count(),
        "records": MedicalRecord.query.count(),
        "open_complaints": Complaint.query.filter(Complaint.status != "Resolved").count(),
        "cafeteria_orders_active": CafeteriaOrder.query.filter(
            CafeteriaOrder.status.in_(["Placed", "Preparing", "Ready"])).count(),
    }
    low_stock = Medicine.query.filter(Medicine.stock_qty < LOW_STOCK_THRESHOLD).limit(5).all()
    near_expiry = Medicine.query.filter(Medicine.expiry_date <= soon).limit(5).all()
    recent_complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(5).all()
    upcoming = (Appointment.query.filter(Appointment.appt_date >= today, Appointment.status == "Booked")
                .order_by(Appointment.appt_date, Appointment.appt_time).limit(6).all())
    stats["pending_leaves"] = DoctorLeave.query.filter_by(status="Pending").count()

    # Appointment load for the next 7 days (bar chart)
    load = []
    for i in range(7):
        d = today + timedelta(days=i)
        n = Appointment.query.filter_by(appt_date=d, status="Booked").count()
        load.append({"label": d.strftime("%a"), "date": d.strftime("%d %b"), "count": n})
    max_load = max([x["count"] for x in load] + [1])

    # Month calendar with booked days marked
    month_days = Appointment.query.filter(
        Appointment.status == "Booked",
        Appointment.appt_date >= today.replace(day=1)).all()
    booked_days = {a.appt_date.day for a in month_days
                   if a.appt_date.year == today.year and a.appt_date.month == today.month}
    weeks = _cal.Calendar(firstweekday=0).monthdayscalendar(today.year, today.month)
    pending_leaves = (DoctorLeave.query.filter_by(status="Pending")
                      .order_by(DoctorLeave.requested_at.desc()).limit(4).all())

    return render_template("auth/admin_dashboard.html", stats=stats, low_stock=low_stock,
                            near_expiry=near_expiry, recent_complaints=recent_complaints, upcoming=upcoming,
                            load=load, max_load=max_load, weeks=weeks, today=today,
                            booked_days=booked_days, month_name=today.strftime("%B %Y"),
                            pending_leaves=pending_leaves)


@auth_bp.route("/doctor/dashboard")
@login_required(roles=["doctor"])
def doctor_dashboard():
    user = get_current_user()
    doctor = user.doctor_profile
    today = date.today()
    todays_appts = (Appointment.query.filter_by(doctor_id=doctor.id, appt_date=today, status="Booked")
                     .order_by(Appointment.appt_time).all())
    upcoming = (Appointment.query.filter(Appointment.doctor_id == doctor.id,
                                          Appointment.appt_date > today, Appointment.status == "Booked")
                .order_by(Appointment.appt_date, Appointment.appt_time).limit(6).all())
    recent_records = (MedicalRecord.query.filter_by(doctor_id=doctor.id)
                       .order_by(MedicalRecord.id.desc()).limit(5).all())
    pending_leave_count = DoctorLeave.query.filter_by(doctor_id=doctor.id, status="Pending").count()
    return render_template("auth/doctor_dashboard.html", doctor=doctor, todays_appts=todays_appts,
                            upcoming=upcoming, recent_records=recent_records,
                            pending_leave_count=pending_leave_count,
                            on_leave_today=doctor_is_on_leave(doctor.id, today))


@auth_bp.route("/patient/dashboard")
@login_required(roles=["patient"])
def patient_dashboard():
    user = get_current_user()
    patient = user.patient_profile
    today = date.today()
    upcoming = (Appointment.query.filter(Appointment.patient_id == patient.id,
                                          Appointment.appt_date >= today, Appointment.status == "Booked")
                .order_by(Appointment.appt_date, Appointment.appt_time).all())
    recent_records = (MedicalRecord.query.filter_by(patient_id=patient.id)
                       .order_by(MedicalRecord.id.desc()).limit(5).all())
    active_orders = (CafeteriaOrder.query.filter_by(user_id=user.id)
                      .filter(CafeteriaOrder.status.notin_(["Delivered", "Cancelled"]))
                      .order_by(CafeteriaOrder.order_date.desc()).all())
    doctor_status = []
    for d in Doctor.query.order_by(Doctor.name).all():
        end = next_leave_end(d.id, today)
        nxt = (DoctorLeave.query.filter(DoctorLeave.doctor_id == d.id, DoctorLeave.status == "Approved",
                                         DoctorLeave.start_date > today)
               .order_by(DoctorLeave.start_date).first())
        doctor_status.append({"doctor": d, "on_leave": end is not None, "back_on": end,
                               "next_leave": nxt})
    return render_template("auth/patient_dashboard.html", patient=patient, upcoming=upcoming,
                            recent_records=recent_records, active_orders=active_orders,
                            doctor_status=doctor_status)


@auth_bp.route("/pharmacy/dashboard")
@login_required(roles=["pharmacy"])
def pharmacy_dashboard():
    today = date.today()
    soon = today + timedelta(days=EXPIRY_WARNING_DAYS)
    stats = {
        "medicines": Medicine.query.count(),
        "low_stock": Medicine.query.filter(Medicine.stock_qty < LOW_STOCK_THRESHOLD).count(),
        "near_expiry": Medicine.query.filter(Medicine.expiry_date <= soon).count(),
    }
    low_stock = Medicine.query.filter(Medicine.stock_qty < LOW_STOCK_THRESHOLD).order_by(Medicine.stock_qty).limit(6).all()
    return render_template("auth/pharmacy_dashboard.html", stats=stats, low_stock=low_stock)


# ---------- Admin: staff management ----------

@auth_bp.route("/admin/staff")
@login_required(roles=["admin"])
def staff_list():
    staff = User.query.filter(User.role.in_(["doctor", "pharmacy", "admin"])).order_by(User.role, User.name).all()
    return render_template("auth/staff_list.html", staff=staff)


@auth_bp.route("/admin/staff/new", methods=["GET", "POST"])
@login_required(roles=["admin"])
def staff_new():
    if request.method == "POST":
        role = request.form.get("role", "")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()

        errors = []
        if role not in ["doctor", "pharmacy", "admin"]:
            errors.append("Select a valid role.")
        if not name:
            errors.append("Name is required.")
        if not email or "@" not in email:
            errors.append("Enter a valid email address.")
        elif User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")

        specialization = request.form.get("specialization", "").strip()
        available_days = request.form.get("available_days", "").strip()
        available_time = request.form.get("available_time", "").strip()
        consultation_fee = request.form.get("consultation_fee", "").strip()
        if role == "doctor" and not specialization:
            errors.append("Specialization is required for a doctor account.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/staff_form.html", form=request.form)

        doctor_id = None
        if role == "doctor":
            fee = float(consultation_fee) if consultation_fee else 500.0
            doctor = Doctor(name=name, specialization=specialization, phone=phone,
                             available_days=available_days, available_time=available_time,
                             consultation_fee=fee)
            db.session.add(doctor)
            db.session.flush()
            doctor_id = doctor.id

        user = User(name=name, email=email, role=role, phone=phone, doctor_id=doctor_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f"{role.capitalize()} account created for {name}.", "success")
        return redirect(url_for("auth.staff_list"))

    return render_template("auth/staff_form.html", form={})


@auth_bp.route("/admin/staff/<int:user_id>/delete", methods=["POST"])
@login_required(roles=["admin"])
def staff_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session.get("user_id"):
        flash("You can't delete the account you're logged in with.", "error")
        return redirect(url_for("auth.staff_list"))
    name = user.name
    db.session.delete(user)
    db.session.commit()
    flash(f"Removed staff account for {name}.", "success")
    return redirect(url_for("auth.staff_list"))
