import os
from flask import Flask
from models import db

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "hms-dev-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'hospital.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["LAB_REPORTS_DIR"] = os.path.join(BASE_DIR, "storage", "lab_reports")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

    db.init_app(app)

    from routes.auth import auth_bp
    from routes.patients import patients_bp
    from routes.doctors import doctors_bp
    from routes.appointments import appointments_bp
    from routes.records import records_bp
    from routes.pharmacy import pharmacy_bp
    from routes.cafeteria import cafeteria_bp
    from routes.complaints import complaints_bp
    from routes.payments import payments_bp
    from routes.leave import leave_bp
    from routes.notifications import notifications_bp
    from routes.lab_reports import lab_reports_bp
    from routes.chatbot import chatbot_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(doctors_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(pharmacy_bp)
    app.register_blueprint(cafeteria_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(lab_reports_bp)
    app.register_blueprint(chatbot_bp)

    from routes.auth_utils import get_current_user

    @app.context_processor
    def inject_current_user():
        return {"current_user": get_current_user()}

    # Make the icon macros available in every template as `icons.name()`
    app.jinja_env.globals["icons"] = app.jinja_env.get_template("_icons.html").module

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
