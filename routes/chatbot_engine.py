"""
Rule-based assistant for the patient portal.

Scope, by design:
  1. Answers "how do I do X on this site" with concrete steps.
  2. Answers doctor-availability questions from real data (approved leave records
     and the doctor's listed hours).
  3. Refuses anything that reads like health/medical advice (symptoms, medicines,
     diagnosis, dosage, prescriptions) and points the patient to book a doctor.

It is a keyword/intent matcher, NOT a general AI model. That is what makes rule 3
reliably enforceable and means no API key is needed.
"""
import re
from datetime import date, timedelta
from models import Doctor, doctor_is_on_leave, next_leave_end

# Health intent is checked FIRST so a medical question can never slip into another branch.
HEALTH_PATTERNS = [
    r"\bpain\b", r"\bache\b", r"\bhurts?\b", r"\bfever\b", r"\bcough", r"\bcold\b", r"\bflu\b",
    r"headache", r"migraine", r"nausea", r"vomit", r"diarr?h?oea", r"\brash\b", r"symptom",
    r"diagnos", r"\bdos(e|age)\b", r"medicine", r"medication", r"tablet", r"\bpills?\b",
    r"antibiotic", r"paracetamol", r"ibuprofen", r"prescri", r"side effects?", r"treat",
    r"\bsick\b", r"illness", r"disease", r"infection", r"allerg", r"bleeding", r"injur",
    r"dizz", r"breath", r"blood pressure", r"\bbp\b", r"sugar", r"diabet", r"covid", r"pregnan",
    r"cancer", r"surgery", r"remed(y|ies)", r"\bcure\b", r"do i have", r"am i (sick|ill)",
    r"is it (normal|serious|safe)", r"should i take", r"what should i do about my",
    r"my (report|result|test)s? (mean|say|show)", r"lab value", r"cholesterol", r"\bchest\b",
    r"stomach", r"throat", r"anxiety", r"depress", r"\bdiet\b", r"weight loss",
]

HOWTO = [
    (["book appointment", "book an appointment", "book a doctor", "book a visit", "schedule appointment",
      "new appointment", "make an appointment", "how do i book", "how to book", "see a doctor"],
     "To book an appointment: open **My Appointments** in the sidebar and click **+ Book appointment**. "
     "Choose a doctor and a date/time. Past dates aren't allowed, and the form tells you straight away "
     "if the doctor is on leave that day. After booking you'll be taken to payment to confirm the slot."),
    (["reschedule", "cancel appointment", "cancel my appointment", "change my appointment", "change appointment"],
     "Go to **My Appointments**. Each upcoming booking has **Reschedule** and **Cancel** buttons. "
     "You can only change your own bookings that are still upcoming."),
    (["view my record", "see my record", "my records", "medical record", "past visits", "consultation history"],
     "Your records are under **My Medical Records** in the sidebar. They appear there automatically "
     "after a doctor adds them for you."),
    (["order food", "cafeteria", "food order", "menu", "order from", "hungry"],
     "Open **Cafeteria → Order Food**, pick items with the + / − buttons, enter your room or "
     "delivery location, and place the order. Then pay to send it to the kitchen. "
     "Track it under **My Orders**."),
    (["complaint", "report issue", "report a problem", "cleaning", "plumbing", "facility", "maintenance",
      "feedback", "leaking", "broken"],
     "Use **Report an Issue** in the sidebar. Pick a category (Cleaning, Plumbing, Electrical, etc.), "
     "enter the room or area, and describe the problem. Admin sees it immediately and you can follow "
     "its status under **My Complaints**."),
    (["lab report", "upload report", "upload my report", "test report", "upload a report", "my reports"],
     "Go to **My Lab Reports** and click **+ Upload a report** to add a PDF or photo from an outside lab. "
     "PDFs are text-scanned automatically. If the test was done in our own lab, the report appears "
     "there by itself and you get a notification."),
    (["payment", "how do i pay", "pay for", "receipt", "invoice"],
     "You're taken to a payment screen right after booking an appointment or placing a cafeteria order. "
     "Past payments are listed under **Payment History**."),
    (["notification", "alert", "bell"],
     "The **bell icon** at the top right shows your alerts: leave changes affecting your appointments, "
     "lab reports ready, order updates and more. Click an alert to jump to the relevant page."),
    (["sign up", "register", "create account", "log in", "login", "password"],
     "Patients sign up from the portal page using **Create an account**. Doctor, pharmacy and admin "
     "accounts are created by the hospital admin."),
]

GREETINGS = ("hi", "hello", "hey", "good morning", "good afternoon", "good evening", "namaste")


def _has(msg, keywords):
    return any(k in msg for k in keywords)


def _doctors_text():
    docs = Doctor.query.order_by(Doctor.name).all()
    if not docs:
        return "There are no doctors on file yet."
    return "Doctors you can book:\n" + "\n".join(f"- Dr. {d.name} — {d.specialization}" for d in docs)


def _find_doctor(msg):
    for d in Doctor.query.all():
        for part in d.name.lower().split():
            if len(part) > 2 and re.search(rf"\b{re.escape(part)}\b", msg):
                return d
    return None


def _target_date(msg):
    if "day after tomorrow" in msg:
        return date.today() + timedelta(days=2), "the day after tomorrow"
    if "tomorrow" in msg:
        return date.today() + timedelta(days=1), "tomorrow"
    m = re.search(r"(\d{4}-\d{2}-\d{2})", msg)
    if m:
        try:
            d = date.fromisoformat(m.group(1))
            return d, d.strftime("on %d %b %Y")
        except ValueError:
            pass
    return date.today(), "today"


def _availability(msg):
    target, label = _target_date(msg)
    if target < date.today():
        return "I can only check today or future dates."
    doctor = _find_doctor(msg)
    if doctor:
        end = next_leave_end(doctor.id, target)
        if end:
            return (f"Dr. {doctor.name} is **on approved leave {label}** "
                    f"({target.strftime('%d %b %Y')}) and returns after {end.strftime('%d %b %Y')}. "
                    f"You can pick another doctor or date when booking.")
        hours = f" Usual hours: {doctor.available_days or 'not set'}, {doctor.available_time or 'not set'}."
        return (f"Dr. {doctor.name} is **available {label}** ({target.strftime('%d %b %Y')}) — "
                f"no approved leave on record.{hours} Book from **My Appointments**.")
    docs = Doctor.query.order_by(Doctor.name).all()
    free = [d for d in docs if not doctor_is_on_leave(d.id, target)]
    away = [d for d in docs if doctor_is_on_leave(d.id, target)]
    lines = [f"Doctors available {label} ({target.strftime('%d %b %Y')}):"]
    lines += [f"- Dr. {d.name} — {d.specialization}" for d in free] or ["- none"]
    if away:
        lines += ["", f"On leave {label}:"] + [f"- Dr. {d.name} — {d.specialization}" for d in away]
    return "\n".join(lines)


def get_reply(message):
    msg = (message or "").strip().lower()
    if not msg:
        return "I didn't catch that. Could you type your question?"

    # 1. Health / medical content is refused before anything else.
    if any(re.search(p, msg) for p in HEALTH_PATTERNS):
        return ("I can't help with symptoms, medicines, prescriptions, reports' meaning or any other "
                "health question. That needs a doctor, not a website assistant. Please book an "
                "appointment from **My Appointments**. If it's urgent, contact hospital reception or "
                "emergency services right away.")

    # 2. Doctor availability (real data)
    asks_avail = _has(msg, ["available", "availability", "on leave", "leave", "working", "free today",
                            "in today", "present", "is dr", "is doctor", "off today"])
    if asks_avail and (_has(msg, ["doctor", "dr ", "dr.", "doctors"]) or _find_doctor(msg)):
        return _availability(msg)

    # 3. Site how-to
    if _has(msg, ["which doctors", "list of doctors", "list doctors", "what doctors", "specialization",
                  "specialisation", "departments", "who are the doctors", "show doctors"]):
        return _doctors_text()
    for keywords, reply in HOWTO:
        if _has(msg, keywords):
            return reply

    if msg.startswith(GREETINGS):
        return ("Hi! I can show you how to do things on this site or tell you whether a doctor is "
                "available. Try: \"how do I book an appointment\" or \"is Dr. Mehra available tomorrow\".")
    if _has(msg, ["thank", "thanks"]):
        return "You're welcome! Ask me anything else about using the site."

    return ("I can help with using this site (appointments, cafeteria, complaints, lab reports, "
            "payments) and with checking whether a doctor is available. I can't answer health or "
            "medical questions. Could you rephrase, or try one of those topics?")
