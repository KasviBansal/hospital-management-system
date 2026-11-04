from flask import Blueprint, request, jsonify
from routes.auth_utils import login_required
from routes.chatbot_engine import get_reply

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/chatbot")


@chatbot_bp.route("/ask", methods=["POST"])
@login_required(roles=["patient"])
def ask():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "Could you type a question?"})
    if len(message) > 300:
        return jsonify({"reply": "That's a bit long. Could you shorten your question?"})
    return jsonify({"reply": get_reply(message)})
