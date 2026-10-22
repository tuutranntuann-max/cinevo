"""Customer-facing local Cinevo assistant."""
from flask import Blueprint, jsonify

from ..ai.chatbot_service import ChatbotService
from ..services.auth_service import current_user_from_request
from ..services.validation import clean_str, json_body

bp = Blueprint("chatbot", __name__, url_prefix="/api/chatbot")


@bp.post("/chat")
def chat():
    data = json_body()
    message = clean_str(data.get("message"), "Tin nhắn", required=True, max_len=500)
    return jsonify(ChatbotService().reply(message, user=current_user_from_request()))
