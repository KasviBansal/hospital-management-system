from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

LOW_STOCK_THRESHOLD = 10
EXPIRY_WARNING_DAYS = 30
CAFETERIA_ITEM_LIMIT = 15

ROLES = ["patient", "doctor", "admin", "pharmacy"]


class User(db.Model):
    """Login account. Every person who can sign in has one of these,
    tagged with a role. Patient/doctor accounts are linked to their
    profile record; admin/pharmacy accounts stand alone."""
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # patient / doctor / admin / pharmacy
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=True)

    patient_profile = db.relationship("Patient", backref=db.backref("user_account", uselist=False), uselist=False,
                                       foreign_keys=[patient_id])
    doctor_profile = db.relationship("Doctor", backref=db.backref("user_account", uselist=False), uselist=False,
                                      foreign_keys=[doctor_id])

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    available_days = db.Column(db.String(120))   # e.g. "Mon,Wed,Fri"
    available_time = db.Column(db.String(60))    # e.g. "10:00 - 14:00"
    consultation_fee = db.Column(db.Float, default=500.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", backref="doctor", lazy=True)
    medical_records = db.relationship("MedicalRecord", backref="doctor", lazy=True)


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", backref="patient", lazy=True, cascade="all, delete-orphan")
    medical_records = db.relationship("MedicalRecord", backref="patient", lazy=True, cascade="all, delete-orphan")


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    appt_date = db.Column(db.Date, nullable=False)
    appt_time = db.Column(db.String(10), nullable=False)  # "HH:MM"
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Booked")  # Booked / Completed / Cancelled
    fee = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default="Pending")  # Pending / Paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    medical_record = db.relationship("MedicalRecord", backref="appointment", uselist=False)


class MedicalRecord(db.Model):
    __tablename__ = "medical_records"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=True)
    diagnosis = db.Column(db.String(255), nullable=False)
    treatment = db.Column(db.Text)
    record_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    prescriptions = db.relationship("Prescription", backref="medical_record", lazy=True, cascade="all, delete-orphan")


class Prescription(db.Model):
    __tablename__ = "prescriptions"
    id = db.Column(db.Integer, primary_key=True)
    medical_record_id = db.Column(db.Integer, db.ForeignKey("medical_records.id"), nullable=False)
    notes = db.Column(db.String(255))
    prescribed_date = db.Column(db.Date, default=date.today)

    items = db.relationship("PrescriptionItem", backref="prescription", lazy=True, cascade="all, delete-orphan")

    @property
    def patient(self):
        return self.medical_record.patient

    @property
    def doctor(self):
        return self.medical_record.doctor


class PrescriptionItem(db.Model):
    __tablename__ = "prescription_items"
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey("prescriptions.id"), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False)
    dosage = db.Column(db.String(120))     # e.g. "1 tablet twice a day"
    quantity = db.Column(db.Integer, nullable=False)
    dispensed_qty = db.Column(db.Integer, default=0)

    medicine = db.relationship("Medicine", backref="prescription_items")

    @property
    def pending_qty(self):
        return self.quantity - self.dispensed_qty

    @property
    def is_fully_dispensed(self):
        return self.dispensed_qty >= self.quantity


class Medicine(db.Model):
    __tablename__ = "medicines"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80))
    stock_qty = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_low_stock(self):
        return self.stock_qty < LOW_STOCK_THRESHOLD

    @property
    def is_near_expiry(self):
        return (self.expiry_date - date.today()).days <= EXPIRY_WARNING_DAYS

    @property
    def is_expired(self):
        return self.expiry_date < date.today()


class DispenseRecord(db.Model):
    __tablename__ = "dispense_records"
    id = db.Column(db.Integer, primary_key=True)
    prescription_item_id = db.Column(db.Integer, db.ForeignKey("prescription_items.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    dispensed_date = db.Column(db.DateTime, default=datetime.utcnow)

    prescription_item = db.relationship("PrescriptionItem", backref="dispense_records")


# ---------------------------------------------------------------------------
# Cafeteria
# ---------------------------------------------------------------------------

class CafeteriaItem(db.Model):
    __tablename__ = "cafeteria_items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60))  # Meals / Beverages / Snacks / Desserts
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    available = db.Column(db.Boolean, default=True)
    image = db.Column(db.String(120), nullable=True)  # file name inside static/img/cafeteria/

    @property
    def image_file(self):
        """Item-specific picture if set, otherwise a category default."""
        if self.image:
            return self.image
        return f"cat_{(self.category or 'meals').lower()}.svg"


class CafeteriaOrder(db.Model):
    __tablename__ = "cafeteria_orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    delivery_location = db.Column(db.String(120), nullable=False)  # e.g. "Room 204" / "Doctor's Lounge"
    status = db.Column(db.String(20), default="Pending Payment")
    # Pending Payment / Placed / Preparing / Ready / Delivered / Cancelled
    payment_status = db.Column(db.String(20), default="Pending")  # Pending / Paid
    total_amount = db.Column(db.Float, default=0.0)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="cafeteria_orders")
    items = db.relationship("CafeteriaOrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class CafeteriaOrderItem(db.Model):
    __tablename__ = "cafeteria_order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("cafeteria_orders.id"), nullable=False)
    cafeteria_item_id = db.Column(db.Integer, db.ForeignKey("cafeteria_items.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_order = db.Column(db.Float, nullable=False)

    cafeteria_item = db.relationship("CafeteriaItem")

    @property
    def subtotal(self):
        return self.quantity * self.price_at_order


# ---------------------------------------------------------------------------
# Complaints / Feedback
# ---------------------------------------------------------------------------

COMPLAINT_CATEGORIES = ["Cleaning", "Plumbing", "Electrical", "Air Conditioning",
                         "Equipment", "Noise", "Other"]


class Complaint(db.Model):
    __tablename__ = "complaints"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    location = db.Column(db.String(120), nullable=False)  # e.g. "Room 204", "Ward 3", "OPD Corridor"
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Open")  # Open / In Progress / Resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref="complaints")


# ---------------------------------------------------------------------------
# Payments (simulated / mock — no real money moves)
# ---------------------------------------------------------------------------

class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # appointment / cafeteria
    reference_id = db.Column(db.Integer, nullable=False)  # Appointment.id or CafeteriaOrder.id
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), default="Mock Card")
    status = db.Column(db.String(20), default="Success")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="payments")


# ---------------------------------------------------------------------------
# Doctor Leave
# ---------------------------------------------------------------------------

class DoctorLeave(db.Model):
    __tablename__ = "doctor_leaves"
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default="Pending")  # Pending / Approved / Rejected
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)
    decided_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    doctor = db.relationship("Doctor", backref="leaves")
    decided_by = db.relationship("User")


def doctor_is_on_leave(doctor_id, on_date):
    """True if the doctor has an APPROVED leave covering on_date."""
    return DoctorLeave.query.filter(
        DoctorLeave.doctor_id == doctor_id,
        DoctorLeave.status == "Approved",
        DoctorLeave.start_date <= on_date,
        DoctorLeave.end_date >= on_date,
    ).first() is not None


def next_leave_end(doctor_id, on_date):
    """If the doctor is on approved leave on on_date, return the last day of that leave."""
    leave = DoctorLeave.query.filter(
        DoctorLeave.doctor_id == doctor_id, DoctorLeave.status == "Approved",
        DoctorLeave.start_date <= on_date, DoctorLeave.end_date >= on_date,
    ).first()
    return leave.end_date if leave else None


# ---------------------------------------------------------------------------
# Notifications (in-app alerts)
# ---------------------------------------------------------------------------

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(20), default="info")  # info / success / warning / alert
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="notifications")


def notify(user_id, message, category="info", link=None):
    """Queue a notification for one user. Caller commits."""
    n = Notification(user_id=user_id, message=message, category=category, link=link)
    db.session.add(n)
    return n


def notify_role(role, message, category="info", link=None):
    for u in User.query.filter_by(role=role).all():
        notify(u.id, message, category, link)


def notify_admins(message, category="info", link=None):
    notify_role("admin", message, category, link)


# ---------------------------------------------------------------------------
# Lab Reports
# ---------------------------------------------------------------------------

class LabReport(db.Model):
    __tablename__ = "lab_reports"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    test_name = db.Column(db.String(160), nullable=False)
    report_date = db.Column(db.Date, default=date.today)
    source = db.Column(db.String(20), default="Patient Upload")  # Patient Upload / Hospital Lab
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # pdf / image
    original_filename = db.Column(db.String(255))
    extracted_text = db.Column(db.Text, nullable=True)  # auto-extracted from PDFs only
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", backref="lab_reports")
    uploaded_by = db.relationship("User")
