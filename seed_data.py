"""
Populates the database with sample data and login accounts for every role,
so the system can be demoed immediately after setup.

Run with: python seed_data.py
"""
from datetime import date, timedelta, datetime
from app import create_app
from models import (db, User, Patient, Doctor, Appointment, MedicalRecord,
                     Prescription, PrescriptionItem, Medicine, CafeteriaItem,
                     CafeteriaOrder, CafeteriaOrderItem, Complaint, Payment,
                     DoctorLeave, Notification, notify, notify_admins)

app = create_app()

IMAGE_FOR = {
    "Veg Thali": "veg_thali.svg", "Chicken Curry with Rice": "chicken_curry.svg",
    "Grilled Sandwich": "grilled_sandwich.svg", "Vegetable Soup": "vegetable_soup.svg",
    "Idli Sambhar": "idli_sambhar.svg", "Poha": "poha.svg", "Fruit Bowl": "fruit_bowl.svg",
    "Curd / Yogurt Cup": "curd_cup.svg", "Masala Chai": "masala_chai.svg",
    "Black Coffee": "black_coffee.svg", "Fresh Lime Water": "lime_water.svg",
    "Mineral Water Bottle": "mineral_water.svg", "Boiled Egg (2 pcs)": "boiled_egg.svg",
    "Khichdi": "khichdi.svg", "Biscuit Pack": "biscuit_pack.svg",
}

CAFETERIA_MENU = [
    ("Veg Thali", "Meals", 120.0, "Dal, rice, two sabzis, roti, and salad."),
    ("Chicken Curry with Rice", "Meals", 160.0, "Home-style chicken curry with steamed rice."),
    ("Grilled Sandwich", "Snacks", 70.0, "Vegetable grilled sandwich with cheese."),
    ("Vegetable Soup", "Meals", 60.0, "Light, warm soup — easy on recovering patients."),
    ("Idli Sambhar", "Meals", 80.0, "Steamed idlis with sambhar and coconut chutney."),
    ("Poha", "Snacks", 50.0, "Light flattened-rice breakfast dish."),
    ("Fruit Bowl", "Desserts", 60.0, "Seasonal fresh fruit, cut and served chilled."),
    ("Curd / Yogurt Cup", "Desserts", 40.0, "Plain probiotic yogurt."),
    ("Masala Chai", "Beverages", 20.0, "Hot spiced tea."),
    ("Black Coffee", "Beverages", 25.0, "Freshly brewed, no sugar added on request."),
    ("Fresh Lime Water", "Beverages", 30.0, "Sweet or salted, served chilled."),
    ("Mineral Water Bottle", "Beverages", 20.0, "500ml sealed bottle."),
    ("Boiled Egg (2 pcs)", "Snacks", 30.0, "Simple protein snack."),
    ("Khichdi", "Meals", 70.0, "Light rice-lentil porridge, easy to digest."),
    ("Biscuit Pack", "Snacks", 15.0, "Assorted glucose biscuits."),
]

with app.app_context():
    if User.query.first():
        print("Database already has data. Skipping seed. "
              "Delete hospital.db and re-run if you want a fresh seed.")
    else:
        # ---------- Admin ----------
        admin = User(name="Hospital Admin", email="admin@hospital.com", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

        # ---------- Doctors ----------
        d1 = Doctor(name="Anjali Mehra", specialization="Cardiology", phone="9876500001",
                    available_days="Mon, Wed, Fri", available_time="10:00 - 14:00", consultation_fee=800.0)
        d2 = Doctor(name="Rohan Kapoor", specialization="General Medicine", phone="9876500002",
                    available_days="Mon - Sat", available_time="09:00 - 17:00", consultation_fee=400.0)
        d3 = Doctor(name="Sana Iyer", specialization="Pediatrics", phone="9876500003",
                    available_days="Tue, Thu, Sat", available_time="11:00 - 15:00", consultation_fee=500.0)
        db.session.add_all([d1, d2, d3])
        db.session.flush()

        doc_user1 = User(name=d1.name, email="anjali.mehra@hospital.com", role="doctor",
                          phone=d1.phone, doctor_id=d1.id)
        doc_user1.set_password("doctor123")
        doc_user2 = User(name=d2.name, email="rohan.kapoor@hospital.com", role="doctor",
                          phone=d2.phone, doctor_id=d2.id)
        doc_user2.set_password("doctor123")
        doc_user3 = User(name=d3.name, email="sana.iyer@hospital.com", role="doctor",
                          phone=d3.phone, doctor_id=d3.id)
        doc_user3.set_password("doctor123")
        db.session.add_all([doc_user1, doc_user2, doc_user3])

        # ---------- Pharmacy staff ----------
        pharm_user = User(name="Karan Bhatia", email="pharmacy@hospital.com", role="pharmacy",
                           phone="9876500099")
        pharm_user.set_password("pharmacy123")
        db.session.add(pharm_user)

        # ---------- Patients ----------
        p1 = Patient(name="Rahul Sharma", age=34, gender="Male", phone="9998887771", address="Patiala, Punjab")
        p2 = Patient(name="Priya Verma", age=28, gender="Female", phone="9998887772", address="Chandigarh")
        p3 = Patient(name="Aarav Singh", age=7, gender="Male", phone="9998887773", address="Patiala, Punjab")
        db.session.add_all([p1, p2, p3])
        db.session.flush()

        pat_user1 = User(name=p1.name, email="rahul.sharma@example.com", role="patient",
                          phone=p1.phone, patient_id=p1.id)
        pat_user1.set_password("patient123")
        pat_user2 = User(name=p2.name, email="priya.verma@example.com", role="patient",
                          phone=p2.phone, patient_id=p2.id)
        pat_user2.set_password("patient123")
        pat_user3 = User(name=p3.name, email="aarav.singh@example.com", role="patient",
                          phone=p3.phone, patient_id=p3.id)
        pat_user3.set_password("patient123")
        db.session.add_all([pat_user1, pat_user2, pat_user3])
        db.session.flush()

        # ---------- Medicines ----------
        m1 = Medicine(name="Paracetamol 500mg", category="Analgesic", stock_qty=200, price=1.50,
                       expiry_date=date.today() + timedelta(days=400))
        m2 = Medicine(name="Amoxicillin 250mg", category="Antibiotic", stock_qty=8, price=6.00,
                       expiry_date=date.today() + timedelta(days=20))
        m3 = Medicine(name="Cetirizine 10mg", category="Antihistamine", stock_qty=150, price=2.00,
                       expiry_date=date.today() + timedelta(days=250))
        m4 = Medicine(name="ORS Sachet", category="Rehydration", stock_qty=60, price=15.00,
                       expiry_date=date.today() + timedelta(days=10))
        db.session.add_all([m1, m2, m3, m4])
        db.session.flush()

        # ---------- Appointments ----------
        a1 = Appointment(patient_id=p1.id, doctor_id=d2.id, appt_date=date.today(),
                          appt_time="10:30", reason="Fever and cold", status="Booked",
                          fee=d2.consultation_fee, payment_status="Pending")
        a2 = Appointment(patient_id=p2.id, doctor_id=d1.id, appt_date=date.today() + timedelta(days=1),
                          appt_time="11:00", reason="Routine heart checkup", status="Booked",
                          fee=d1.consultation_fee, payment_status="Paid")
        a3 = Appointment(patient_id=p3.id, doctor_id=d3.id, appt_date=date.today() - timedelta(days=2),
                          appt_time="12:00", reason="Vaccination follow-up", status="Completed",
                          fee=d3.consultation_fee, payment_status="Paid")
        db.session.add_all([a1, a2, a3])
        db.session.flush()

        db.session.add(Payment(user_id=pat_user2.id, purpose="appointment", reference_id=a2.id,
                                amount=d1.consultation_fee, method="Mock Card", status="Success"))
        db.session.add(Payment(user_id=pat_user3.id, purpose="appointment", reference_id=a3.id,
                                amount=d3.consultation_fee, method="Mock UPI", status="Success"))

        # Medical record + prescription for the completed appointment
        rec = MedicalRecord(patient_id=p3.id, doctor_id=d3.id, appointment_id=a3.id,
                             diagnosis="Mild seasonal flu", treatment="Rest, fluids, and antihistamine course.",
                             record_date=a3.appt_date)
        db.session.add(rec)
        db.session.flush()

        pres = Prescription(medical_record_id=rec.id, notes="Take after meals", prescribed_date=rec.record_date)
        db.session.add(pres)
        db.session.flush()

        db.session.add_all([
            PrescriptionItem(prescription_id=pres.id, medicine_id=m3.id, dosage="1 tsp once daily", quantity=10),
            PrescriptionItem(prescription_id=pres.id, medicine_id=m1.id, dosage="1 tablet if fever", quantity=6),
        ])

        # ---------- Cafeteria menu (15 items) ----------
        cafeteria_items = []
        for name, category, price, description in CAFETERIA_MENU:
            item = CafeteriaItem(name=name, category=category, price=price,
                                  description=description, available=True,
                                  image=IMAGE_FOR.get(name))
            db.session.add(item)
            cafeteria_items.append(item)
        db.session.flush()

        # Sample cafeteria order (paid, placed) for patient 1
        order = CafeteriaOrder(user_id=pat_user1.id, delivery_location="Room 204",
                                status="Placed", payment_status="Paid",
                                total_amount=cafeteria_items[0].price + cafeteria_items[8].price)
        db.session.add(order)
        db.session.flush()
        db.session.add_all([
            CafeteriaOrderItem(order_id=order.id, cafeteria_item_id=cafeteria_items[0].id,
                                quantity=1, price_at_order=cafeteria_items[0].price),
            CafeteriaOrderItem(order_id=order.id, cafeteria_item_id=cafeteria_items[8].id,
                                quantity=1, price_at_order=cafeteria_items[8].price),
        ])
        db.session.add(Payment(user_id=pat_user1.id, purpose="cafeteria", reference_id=order.id,
                                amount=order.total_amount, method="Mock Card", status="Success"))

        # ---------- Sample complaint ----------
        db.session.add(Complaint(user_id=pat_user1.id, category="Plumbing", location="Room 204",
                                  description="Bathroom tap is leaking continuously.", status="Open"))
        db.session.add(Complaint(user_id=doc_user2.id, category="Air Conditioning", location="OPD-2",
                                  description="AC not cooling in consultation room 2.", status="In Progress"))

        # ---------- Sample leave requests + alerts ----------
        db.session.add(DoctorLeave(doctor_id=d2.id, start_date=date.today() + timedelta(days=3),
                                    end_date=date.today() + timedelta(days=5),
                                    reason="Medical conference", status="Pending"))
        db.session.add(DoctorLeave(doctor_id=d1.id, start_date=date.today() + timedelta(days=10),
                                    end_date=date.today() + timedelta(days=12),
                                    reason="Family function", status="Approved"))
        db.session.flush()
        notify_admins("Dr. Rohan Kapoor requested leave for Medical conference.", "info", "/leave/admin")
        notify(pat_user1.id, "Welcome to HMS! Use the chat button to ask how to use the site.", "info")
        notify(pat_user1.id, "Payment pending for your upcoming appointment.", "warning", "/pay/history")
        notify(doc_user1.id, "Your leave request has been approved.", "success", "/leave/my")

        db.session.commit()
        print("Seed data created successfully.\n")
        print("Login accounts (email / password):")
        print("  Admin:     admin@hospital.com / admin123")
        print("  Doctor:    anjali.mehra@hospital.com / doctor123  (Cardiology)")
        print("  Doctor:    rohan.kapoor@hospital.com / doctor123  (General Medicine)")
        print("  Doctor:    sana.iyer@hospital.com / doctor123     (Pediatrics)")
        print("  Pharmacy:  pharmacy@hospital.com / pharmacy123")
        print("  Patient:   rahul.sharma@example.com / patient123")
        print("  Patient:   priya.verma@example.com / patient123")
        print("  Patient:   aarav.singh@example.com / patient123")
