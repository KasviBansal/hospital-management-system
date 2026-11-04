# Hospital Management System (v2 — multi-role)

A Flask + SQLite web application with four separate portals — **Patient**,
**Doctor**, **Admin**, and **Pharmacy** — each with its own login and
dashboard, built on top of the original three-component design (Patient &
Appointment Management, Medical Records & Report Management, Pharmacy &
Medicine Management), plus a Cafeteria module, a Complaints/Feedback
module, and a simulated Payment portal.

## 1. Setup

Requires Python 3.9+.

```bash
cd hms
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Load demo accounts and sample data

```bash
python seed_data.py
```

This creates one login for each role so you can demo every portal immediately:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@hospital.com` | `admin123` |
| Doctor (Cardiology) | `anjali.mehra@hospital.com` | `doctor123` |
| Doctor (General Medicine) | `rohan.kapoor@hospital.com` | `doctor123` |
| Doctor (Pediatrics) | `sana.iyer@hospital.com` | `doctor123` |
| Pharmacy staff | `pharmacy@hospital.com` | `pharmacy123` |
| Patient | `rahul.sharma@example.com` | `patient123` |
| Patient | `priya.verma@example.com` | `patient123` |
| Patient | `aarav.singh@example.com` | `patient123` |

It also creates 15 cafeteria menu items, a sample appointment, medical
record, prescription, cafeteria order, and two complaints.

Skip this step if you'd rather start empty — the database and tables are
created automatically the first time you run the app, but you'll only have
the Admin-created-via-signup-page patient accounts and whatever you add by
hand (there is no bootstrap admin without seeding — see note below).

## 3. Run the app

```bash
python app.py
```

Open **http://127.0.0.1:5000** — you'll land on the portal picker.

To start completely fresh, stop the server, delete `hospital.db`, and
re-run `python app.py` (and `seed_data.py` if you want demo data again).

> **Note:** if you skip `seed_data.py`, there is no admin account to log
> into, since only patients can self-register. Run the seed script at
> least once, or manually insert an admin user with a Python shell using
> `User(...).set_password(...)`.

## 4. How accounts work

- **Patients** self-register from the portal page (`Sign up`). No approval
  needed — this matches how a real hospital's online booking portal works.
- **Doctors and Pharmacy staff** cannot self-register. An Admin creates
  their account from **Manage Staff → Add staff account**, which also
  creates their profile (specialization, fee, availability for doctors).
- **Admins** can also create additional Admin accounts from the same page.

Each login is tied to exactly one role. Logging in through the wrong
portal (e.g. a doctor's email on the Patient login page) is rejected with
a message telling you which portal to use instead.

## 5. What each portal can do

**Patient**
- Book an appointment with any doctor (conflict-checked against the
  doctor's schedule), pay the consultation fee (simulated), reschedule or
  cancel their own upcoming appointments.
- View their own medical records and prescriptions (read-only).
- Order from the cafeteria menu, pay (simulated), track order status.
- Submit facility complaints (cleaning, plumbing, etc.) and track status.
- View their own payment history.

**Doctor**
- See today's schedule and upcoming appointments (their own only).
- Mark an appointment "Completed", which opens straight into adding a
  medical record for that visit.
- Add medical records and prescriptions for their patients.
- Order from the cafeteria (e.g. for delivery to the doctors' lounge).
- Submit facility complaints and track their own.
- View their own payment history.

**Admin**
- Full patient and doctor directory management.
- Create/remove Doctor, Pharmacy, and Admin login accounts.
- View and manage all appointments, records, and prescriptions.
- Manage the cafeteria menu (capped at 15 items) and track/update all
  cafeteria orders.
- Triage all complaints — reassign status (Open / In Progress / Resolved).
- View all payments hospital-wide.
- Same Pharmacy access as pharmacy staff (oversight).

**Pharmacy staff**
- Manage medicine inventory (stock, price, expiry).
- Work the dispense queue against prescriptions, with stock and
  over-dispense guards.
- View the pharmacy billing log.

## 6. Payments — how they work here

The payment portal is **simulated for demo/viva purposes — no real money
moves, and no real payment gateway is contacted.** It's used for two
things:

1. **Appointment booking** — after booking, the appointment is created
   with `payment_status = Pending`. The slot is already reserved (so it
   still blocks double-booking), but a "Pay now" prompt shows until paid.
2. **Cafeteria orders** — after placing an order, it sits as
   `Pending Payment` until paid; once paid, it becomes `Placed` and moves
   into the admin's fulfillment queue (Preparing → Ready → Delivered).

The mock payment form accepts any card-like input (any digits work) and
always succeeds — there's no real validation beyond basic formatting,
by design.

## 7. Cafeteria menu cap

The menu is capped at **15 items** (`CAFETERIA_ITEM_LIMIT` in `models.py`).
Once 15 items exist, Admin must remove one before adding another — this
is enforced server-side, not just hidden in the UI.

## 8. Project structure

```
hms/
├── app.py                     # App factory, blueprint registration, current-user context
├── models.py                   # All database tables (SQLAlchemy models)
├── seed_data.py                  # Demo accounts + sample data loader
├── requirements.txt
├── routes/
│   ├── auth.py                 # Portal, per-role login, signup, dashboards, staff management
│   ├── auth_utils.py            # login_required decorator, current-user helper
│   ├── patients.py              # Admin — patient master data CRUD
│   ├── doctors.py                # Admin — doctor directory CRUD
│   ├── appointments.py            # Booking, reschedule, cancel, complete (role-aware)
│   ├── records.py                 # Medical records + prescriptions (role-aware)
│   ├── pharmacy.py                 # Inventory, dispensing, billing (pharmacy + admin)
│   ├── cafeteria.py                 # Menu, ordering, order tracking
│   ├── complaints.py                  # Facility issue reporting + admin triage
│   └── payments.py                    # Simulated payment processing
├── templates/
│   ├── auth/                   # Portal, login, signup, about, 4 dashboards, staff mgmt
│   ├── cafeteria/                # Menu, my orders, admin menu + orders
│   ├── complaints/                # Report form, my complaints, admin inbox
│   ├── payments/                   # Mock payment page, payment history
│   ├── patients/, doctors/, appointments/, records/, prescriptions/, medicines/, dispense/
│   ├── base.html                  # Authenticated layout (role-aware sidebar)
│   └── public_base.html            # Unauthenticated layout (portal/login/signup/about)
└── static/css/style.css        # All styling
```

## 9. Access control model

Every route is gated by a `login_required(roles=[...])` decorator (see
`routes/auth_utils.py`). Beyond role-level gating, several routes also
check **ownership** — e.g. a patient can only reschedule their own
appointment, a doctor can only edit medical records they created, and
viewing a medical record checks that the requester is the treating doctor,
the patient it belongs to, or an admin. Unauthorized access attempts
return a 403 rather than silently showing the wrong data.

## 10. Team / division of work

The original three core components map to these members and files, with
the new modules added on top:

| Member | Component | Core files |
|---|---|---|
| Shubhangi Gupta | Patient & Appointment Management | `routes/patients.py`, `routes/doctors.py`, `routes/appointments.py` |
| Kasvi Bansal | Medical Records & Report Management | `routes/records.py`, `templates/records/`, `templates/prescriptions/` |
| Twisha Jain | Pharmacy & Medicine Management | `routes/pharmacy.py`, `templates/medicines/`, `templates/dispense/` |

Shared / new additions: `models.py`, `app.py`, `routes/auth.py`,
`routes/cafeteria.py`, `routes/complaints.py`, `routes/payments.py`.

---
## v3 additions
- Dates in the past are rejected (appointments, leave) on both browser and server.
- Doctors request leave (`/leave/new`); admin approves/rejects at **Leave Requests**. Approved leave blocks booking and shows "On leave" to patients.
- Lab Reports: patients upload PDF/image (PDF text auto-extracted); admin ("Hospital Lab") can send reports to a patient.
- In-app alerts: bell icon + toast popups.
- Patient-only Help Assistant (rule-based): explains how to use the site and doctor availability; refuses health/medicine questions.
- Cafeteria images are generated by `tools/gen_food_svgs.py`.
- New look: teal sidebar, topbar search, dark mode toggle.
- Run: `pip install -r requirements.txt`, then `python seed_data.py`, then `python app.py` (on Windows use `python`/`py`).
New logins: see seed_data output (admin@hospital.com / admin123, etc.).
