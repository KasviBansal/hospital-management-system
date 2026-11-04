from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models import db, CafeteriaItem, CafeteriaOrder, CafeteriaOrderItem, CAFETERIA_ITEM_LIMIT
from routes.auth_utils import login_required, get_current_user

cafeteria_bp = Blueprint("cafeteria", __name__, url_prefix="/cafeteria")
cafeteria_bp.before_request(login_required(roles=["admin", "doctor", "patient"])(lambda: None))


# ---------- Ordering (patient / doctor) ----------

@cafeteria_bp.route("/menu", methods=["GET", "POST"])
@login_required(roles=["doctor", "patient"])
def menu():
    user = get_current_user()
    items = CafeteriaItem.query.filter_by(available=True).order_by(CafeteriaItem.category, CafeteriaItem.name).all()

    if request.method == "POST":
        delivery_location = request.form.get("delivery_location", "").strip()
        errors = []
        if not delivery_location:
            errors.append("Enter a delivery location (e.g. Room number or department).")

        order_lines = []
        for item in items:
            qty_raw = request.form.get(f"qty_{item.id}", "0").strip()
            qty = int(qty_raw) if qty_raw.isdigit() else 0
            if qty > 0:
                order_lines.append((item, qty))

        if not order_lines:
            errors.append("Select at least one item and quantity.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("cafeteria/menu.html", items=items)

        total = sum(item.price * qty for item, qty in order_lines)
        order = CafeteriaOrder(user_id=user.id, delivery_location=delivery_location,
                                status="Pending Payment", payment_status="Pending", total_amount=total)
        db.session.add(order)
        db.session.flush()

        for item, qty in order_lines:
            db.session.add(CafeteriaOrderItem(order_id=order.id, cafeteria_item_id=item.id,
                                               quantity=qty, price_at_order=item.price))
        db.session.commit()
        flash("Order placed. Complete payment to send it to the kitchen.", "success")
        return redirect(url_for("payments.pay", purpose="cafeteria", reference_id=order.id))

    return render_template("cafeteria/menu.html", items=items)


@cafeteria_bp.route("/my-orders")
@login_required(roles=["doctor", "patient"])
def my_orders():
    user = get_current_user()
    orders = (CafeteriaOrder.query.filter_by(user_id=user.id)
              .order_by(CafeteriaOrder.order_date.desc()).all())
    return render_template("cafeteria/my_orders.html", orders=orders)


# ---------- Admin: menu + order management ----------

@cafeteria_bp.route("/admin/menu")
@login_required(roles=["admin"])
def admin_menu():
    items = CafeteriaItem.query.order_by(CafeteriaItem.category, CafeteriaItem.name).all()
    return render_template("cafeteria/admin_menu.html", items=items, limit=CAFETERIA_ITEM_LIMIT)


@cafeteria_bp.route("/admin/menu/new", methods=["GET", "POST"])
@login_required(roles=["admin"])
def admin_menu_new():
    count = CafeteriaItem.query.count()
    if count >= CAFETERIA_ITEM_LIMIT:
        flash(f"The cafeteria menu is capped at {CAFETERIA_ITEM_LIMIT} items. "
              f"Remove an item before adding a new one.", "error")
        return redirect(url_for("cafeteria.admin_menu"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        price = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()

        errors = []
        if not name:
            errors.append("Item name is required.")
        try:
            price_val = float(price)
            if price_val < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Enter a valid price.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("cafeteria/admin_menu_form.html", item=None, form=request.form)

        db.session.add(CafeteriaItem(name=name, category=category, price=float(price),
                                      description=description, available=True))
        db.session.commit()
        flash(f"Added '{name}' to the cafeteria menu.", "success")
        return redirect(url_for("cafeteria.admin_menu"))

    return render_template("cafeteria/admin_menu_form.html", item=None, form={})


@cafeteria_bp.route("/admin/menu/<int:item_id>/edit", methods=["GET", "POST"])
@login_required(roles=["admin"])
def admin_menu_edit(item_id):
    item = CafeteriaItem.query.get_or_404(item_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        price = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()
        available = request.form.get("available") == "on"

        errors = []
        if not name:
            errors.append("Item name is required.")
        try:
            price_val = float(price)
            if price_val < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Enter a valid price.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("cafeteria/admin_menu_form.html", item=item, form=request.form)

        item.name = name
        item.category = category
        item.price = float(price)
        item.description = description
        item.available = available
        db.session.commit()
        flash("Menu item updated.", "success")
        return redirect(url_for("cafeteria.admin_menu"))

    form = {"name": item.name, "category": item.category, "price": item.price,
            "description": item.description}
    return render_template("cafeteria/admin_menu_form.html", item=item, form=form)


@cafeteria_bp.route("/admin/menu/<int:item_id>/delete", methods=["POST"])
@login_required(roles=["admin"])
def admin_menu_delete(item_id):
    item = CafeteriaItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f"Removed '{item.name}' from the menu.", "success")
    return redirect(url_for("cafeteria.admin_menu"))


@cafeteria_bp.route("/admin/orders")
@login_required(roles=["admin"])
def admin_orders():
    orders = CafeteriaOrder.query.order_by(CafeteriaOrder.order_date.desc()).all()
    return render_template("cafeteria/admin_orders.html", orders=orders)


@cafeteria_bp.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@login_required(roles=["admin"])
def admin_order_status(order_id):
    order = CafeteriaOrder.query.get_or_404(order_id)
    new_status = request.form.get("status", "")
    if new_status in ["Preparing", "Ready", "Delivered", "Cancelled"]:
        order.status = new_status
        from models import notify
        notify(order.user_id, f"Your cafeteria order #{order.id} is now {new_status.lower()}.",
               "success" if new_status in ("Ready", "Delivered") else "info", url_for("cafeteria.my_orders"))
        db.session.commit()
        flash(f"Order #{order.id} marked as {new_status}.", "success")
    return redirect(url_for("cafeteria.admin_orders"))
