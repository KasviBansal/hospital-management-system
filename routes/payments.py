from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models import db, Payment, Appointment, CafeteriaOrder, notify, notify_admins
from routes.auth_utils import login_required, get_current_user

payments_bp = Blueprint("payments", __name__, url_prefix="/pay")
payments_bp.before_request(login_required(roles=["admin", "doctor", "patient"])(lambda: None))


def _load_reference(purpose, reference_id, user):
    if purpose == "appointment":
        obj = Appointment.query.get_or_404(reference_id)
        if user.role == "patient" and obj.patient_id != user.patient_profile.id:
            abort(403)
        return obj
    elif purpose == "cafeteria":
        obj = CafeteriaOrder.query.get_or_404(reference_id)
        if user.role in ("patient", "doctor") and obj.user_id != user.id:
            abort(403)
        return obj
    abort(404)


@payments_bp.route("/<purpose>/<int:reference_id>", methods=["GET", "POST"])
def pay(purpose, reference_id):
    if purpose not in ("appointment", "cafeteria"):
        abort(404)
    user = get_current_user()
    obj = _load_reference(purpose, reference_id, user)

    already_paid = obj.payment_status == "Paid"
    amount = obj.fee if purpose == "appointment" else obj.total_amount

    if request.method == "POST" and not already_paid:
        method = request.form.get("method", "Mock Card")
        card_number = request.form.get("card_number", "").strip()
        expiry = request.form.get("expiry", "").strip()
        cvv = request.form.get("cvv", "").strip()

        errors = []
        if method == "Mock Card":
            if not (card_number.replace(" ", "").isdigit() and len(card_number.replace(" ", "")) >= 12):
                errors.append("Enter a valid card number (this is a simulated payment — any digits work).")
            if not expiry:
                errors.append("Enter an expiry date.")
            if not (cvv.isdigit() and len(cvv) in (3, 4)):
                errors.append("Enter a valid CVV.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("payments/pay.html", purpose=purpose, obj=obj, amount=amount,
                                    already_paid=already_paid)

        payment = Payment(user_id=user.id, purpose=purpose, reference_id=obj.id,
                           amount=amount, method=method, status="Success")
        db.session.add(payment)

        obj.payment_status = "Paid"
        if purpose == "cafeteria":
            obj.status = "Placed"
            notify(user.id, f"Payment received. Cafeteria order #{obj.id} has been sent to the kitchen.",
                   "success", url_for("cafeteria.my_orders"))
            notify_admins(f"New cafeteria order #{obj.id} for {obj.delivery_location}.",
                          "info", url_for("cafeteria.admin_orders"))
        else:
            notify(user.id, f"Appointment with Dr. {obj.doctor.name} on "
                            f"{obj.appt_date.strftime('%d %b %Y')} at {obj.appt_time} is confirmed.",
                   "success", url_for("appointments.list_appointments"))
            if obj.doctor.user_account:
                notify(obj.doctor.user_account.id,
                       f"New appointment: {obj.patient.name} on {obj.appt_date.strftime('%d %b %Y')} "
                       f"at {obj.appt_time}.", "info", url_for("appointments.list_appointments"))
        db.session.commit()

        flash(f"Payment of Rs. {amount:.2f} successful (simulated). "
              f"{'Appointment confirmed.' if purpose == 'appointment' else 'Order sent to the kitchen.'}",
              "success")

        if purpose == "appointment":
            return redirect(url_for("appointments.list_appointments"))
        return redirect(url_for("cafeteria.my_orders"))

    return render_template("payments/pay.html", purpose=purpose, obj=obj, amount=amount,
                            already_paid=already_paid)


@payments_bp.route("/history")
@login_required(roles=["admin", "doctor", "patient"])
def history():
    user = get_current_user()
    query = Payment.query
    if user.role != "admin":
        query = query.filter_by(user_id=user.id)
    payments = query.order_by(Payment.created_at.desc()).all()
    return render_template("payments/history.html", payments=payments, is_admin=(user.role == "admin"))
