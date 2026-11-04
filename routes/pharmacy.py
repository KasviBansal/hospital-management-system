from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Medicine, PrescriptionItem, Prescription, DispenseRecord, LOW_STOCK_THRESHOLD, EXPIRY_WARNING_DAYS
from routes.auth_utils import login_required

pharmacy_bp = Blueprint("pharmacy", __name__, url_prefix="/pharmacy")
pharmacy_bp.before_request(login_required(roles=["pharmacy", "admin"])(lambda: None))


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ---------- Medicine inventory ----------

@pharmacy_bp.route("/medicines")
def list_medicines():
    q = request.args.get("q", "").strip()
    filter_type = request.args.get("filter", "")
    query = Medicine.query
    if q:
        query = query.filter(Medicine.name.ilike(f"%{q}%"))
    medicines = query.order_by(Medicine.name).all()

    if filter_type == "low_stock":
        medicines = [m for m in medicines if m.is_low_stock]
    elif filter_type == "near_expiry":
        medicines = [m for m in medicines if m.is_near_expiry]

    return render_template("medicines/list.html", medicines=medicines, q=q, filter_type=filter_type)


@pharmacy_bp.route("/medicines/new", methods=["GET", "POST"])
def new_medicine():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        stock_qty = request.form.get("stock_qty", "").strip()
        price = request.form.get("price", "").strip()
        expiry_date = _parse_date(request.form.get("expiry_date", ""))

        errors = []
        if not name:
            errors.append("Medicine name is required.")
        if not stock_qty.isdigit():
            errors.append("Enter a valid stock quantity.")
        try:
            price_val = float(price)
            if price_val < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Enter a valid price.")
        if not expiry_date:
            errors.append("Enter a valid expiry date.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("medicines/form.html", medicine=None, form=request.form)

        medicine = Medicine(name=name, category=category, stock_qty=int(stock_qty),
                             price=float(price), expiry_date=expiry_date)
        db.session.add(medicine)
        db.session.commit()
        flash(f"Medicine '{name}' added to inventory.", "success")
        return redirect(url_for("pharmacy.list_medicines"))

    return render_template("medicines/form.html", medicine=None, form={})


@pharmacy_bp.route("/medicines/<int:medicine_id>/edit", methods=["GET", "POST"])
def edit_medicine(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        stock_qty = request.form.get("stock_qty", "").strip()
        price = request.form.get("price", "").strip()
        expiry_date = _parse_date(request.form.get("expiry_date", ""))

        errors = []
        if not name:
            errors.append("Medicine name is required.")
        if not stock_qty.isdigit():
            errors.append("Enter a valid stock quantity.")
        try:
            price_val = float(price)
            if price_val < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Enter a valid price.")
        if not expiry_date:
            errors.append("Enter a valid expiry date.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("medicines/form.html", medicine=medicine, form=request.form)

        medicine.name = name
        medicine.category = category
        medicine.stock_qty = int(stock_qty)
        medicine.price = float(price)
        medicine.expiry_date = expiry_date
        db.session.commit()
        flash("Medicine details updated.", "success")
        return redirect(url_for("pharmacy.list_medicines"))

    form = {"name": medicine.name, "category": medicine.category, "stock_qty": medicine.stock_qty,
            "price": medicine.price, "expiry_date": medicine.expiry_date.isoformat()}
    return render_template("medicines/form.html", medicine=medicine, form=form)


@pharmacy_bp.route("/medicines/<int:medicine_id>/delete", methods=["POST"])
def delete_medicine(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    db.session.delete(medicine)
    db.session.commit()
    flash(f"Medicine '{medicine.name}' removed from inventory.", "success")
    return redirect(url_for("pharmacy.list_medicines"))


# ---------- Dispensing ----------

@pharmacy_bp.route("/dispense")
def dispense_queue():
    """Show prescription items that are still pending dispensing."""
    items = (PrescriptionItem.query.join(Prescription)
             .filter(PrescriptionItem.dispensed_qty < PrescriptionItem.quantity)
             .order_by(Prescription.prescribed_date.desc()).all())
    return render_template("dispense/list.html", items=items)


@pharmacy_bp.route("/dispense/<int:item_id>", methods=["GET", "POST"])
def dispense_item(item_id):
    item = PrescriptionItem.query.get_or_404(item_id)
    medicine = item.medicine

    if request.method == "POST":
        qty = request.form.get("quantity", "").strip()

        errors = []
        if not qty.isdigit() or int(qty) <= 0:
            errors.append("Enter a valid quantity to dispense.")
        else:
            qty = int(qty)
            if qty > item.pending_qty:
                errors.append(f"Cannot dispense more than the pending quantity ({item.pending_qty}).")
            if qty > medicine.stock_qty:
                errors.append(f"Insufficient stock. Only {medicine.stock_qty} units of "
                               f"'{medicine.name}' available.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("dispense/form.html", item=item, medicine=medicine)

        amount = qty * medicine.price
        medicine.stock_qty -= qty
        item.dispensed_qty += qty
        db.session.add(DispenseRecord(prescription_item_id=item.id, quantity=qty, amount=amount))
        from models import notify_role
        if medicine.is_low_stock:
            for role in ("pharmacy", "admin"):
                notify_role(role, f"Low stock: {medicine.name} has only {medicine.stock_qty} units left.",
                            "alert", url_for("pharmacy.list_medicines", filter="low_stock"))
        patient_user = item.prescription.patient.user_account
        if patient_user and item.is_fully_dispensed:
            from models import notify
            notify(patient_user.id, f"Your medicine '{medicine.name}' has been dispensed.",
                   "success", url_for("records.list_records"))
        db.session.commit()
        flash(f"Dispensed {qty} unit(s) of '{medicine.name}'. Bill amount: Rs. {amount:.2f}", "success")
        return redirect(url_for("pharmacy.dispense_queue"))

    return render_template("dispense/form.html", item=item, medicine=medicine)


@pharmacy_bp.route("/billing")
def billing():
    records = DispenseRecord.query.order_by(DispenseRecord.dispensed_date.desc()).all()
    total = sum(r.amount for r in records)
    return render_template("dispense/billing.html", records=records, total=total)
