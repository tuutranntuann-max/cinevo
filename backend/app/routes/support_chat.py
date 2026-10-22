"""Authenticated customer-to-staff support chat APIs."""
from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_USER,
    SupportAssignment, SupportConversation, SupportMessage,
)
from ..services.auth_service import roles_required
from ..services.validation import ApiError, clean_int, clean_str, json_body
from ..timeutil import utc_now

bp = Blueprint("support_chat", __name__, url_prefix="/api/support")
customer_only = roles_required(ROLE_USER)
STAFF_ROLES = (ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN)
staff_only = roles_required(*STAFF_ROLES)
MESSAGE_LIMIT = 2000
HISTORY_LIMIT = 100


def _conversation_for_customer(conversation_id):
    conversation = db.session.get(SupportConversation, conversation_id)
    if not conversation or conversation.customer_id != g.current_user.id:
        raise ApiError("Không tìm thấy cuộc trò chuyện.", 404)
    return conversation


def _conversation_for_staff(conversation_id):
    conversation = db.session.get(SupportConversation, conversation_id)
    if not conversation:
        raise ApiError("Không tìm thấy cuộc trò chuyện.", 404)
    return conversation


def _messages_response(conversation, *, staff):
    raw_after = request.args.get("after_id")
    after_id = clean_int(raw_after, "Mốc tin nhắn", lo=0) if raw_after is not None else None
    query = SupportMessage.query.filter_by(conversation_id=conversation.id)
    if after_id is not None:
        query = query.filter(SupportMessage.id > after_id)
        messages = query.order_by(SupportMessage.id.asc()).limit(HISTORY_LIMIT).all()
    else:
        messages = (
            query.order_by(SupportMessage.id.desc())
            .limit(HISTORY_LIMIT)
            .all()
        )
        messages.reverse()

    if messages:
        last_read_id = messages[-1].id
        if staff:
            conversation.staff_last_read_message_id = max(
                conversation.staff_last_read_message_id, last_read_id
            )
        else:
            conversation.customer_last_read_message_id = max(
                conversation.customer_last_read_message_id, last_read_id
            )
    if staff:
        conversation.staff_notified = True
    if messages or staff:
        db.session.commit()

    return jsonify({
        "conversation": conversation.to_dict(),
        "messages": [message.to_dict() for message in messages],
        "has_earlier": SupportMessage.query.filter(
            SupportMessage.conversation_id == conversation.id,
            SupportMessage.id < (messages[0].id if messages else 0),
        ).first() is not None if after_id is None else False,
    })


def _latest_message(conversation_id):
    message = (
        SupportMessage.query.filter_by(conversation_id=conversation_id)
        .order_by(SupportMessage.id.desc())
        .first()
    )
    return message.to_dict() if message else None


def _staff_unread_count(conversation):
    unread_messages = SupportMessage.query.filter(
        SupportMessage.conversation_id == conversation.id,
        SupportMessage.sender_role == ROLE_USER,
        SupportMessage.id > conversation.staff_last_read_message_id,
    ).count()
    if unread_messages:
        return unread_messages
    has_messages = SupportMessage.query.filter_by(conversation_id=conversation.id).first() is not None
    return int(not has_messages and not conversation.staff_notified)


def _customer_unread_count(conversation):
    return SupportMessage.query.filter(
        SupportMessage.conversation_id == conversation.id,
        SupportMessage.sender_role.in_(STAFF_ROLES),
        SupportMessage.id > conversation.customer_last_read_message_id,
    ).count()


@bp.get("/conversation")
@customer_only
def get_customer_conversation():
    conversation = (
        SupportConversation.query.filter_by(customer_id=g.current_user.id, status="open")
        .order_by(SupportConversation.updated_at.desc())
        .first()
    )
    if not conversation:
        return jsonify(None)
    messages = (
        SupportMessage.query.filter_by(conversation_id=conversation.id)
        .order_by(SupportMessage.id.desc())
        .limit(HISTORY_LIMIT)
        .all()[::-1]
    )
    if messages:
        conversation.customer_last_read_message_id = max(
            conversation.customer_last_read_message_id, messages[-1].id
        )
        db.session.commit()
    return jsonify({
        **conversation.to_dict(unread_count=_customer_unread_count(conversation)),
        "messages": [message.to_dict() for message in messages],
    })


@bp.post("/conversation")
@customer_only
def start_customer_conversation():
    conversation = (
        SupportConversation.query.filter_by(customer_id=g.current_user.id, status="open")
        .order_by(SupportConversation.updated_at.desc())
        .first()
    )
    if conversation is None:
        conversation = SupportConversation(customer_id=g.current_user.id)
        db.session.add(conversation)
        db.session.commit()
        status = 201
    else:
        status = 200
    return jsonify({
        **conversation.to_dict(unread_count=_customer_unread_count(conversation)),
        "messages": [],
    }), status


@bp.post("/conversation/<int:conversation_id>/messages")
@customer_only
def send_customer_message(conversation_id):
    conversation = _conversation_for_customer(conversation_id)
    if conversation.status != "open":
        raise ApiError("Cuộc trò chuyện đã kết thúc. Hãy bắt đầu cuộc trò chuyện mới.", 409)
    data = json_body()
    body = clean_str(data.get("body"), "Tin nhắn", min_len=1, max_len=MESSAGE_LIMIT, required=True)
    first_customer_message = not SupportMessage.query.filter_by(
        conversation_id=conversation.id,
        sender_role=ROLE_USER,
    ).first()
    message = SupportMessage(
        conversation_id=conversation.id,
        sender_id=g.current_user.id,
        sender_role=g.current_user.role.name,
        body=body,
    )
    conversation.updated_at = utc_now()
    db.session.add(message)
    if first_customer_message and not conversation.assignment:
        db.session.add(SupportMessage(
            conversation_id=conversation.id,
            sender_id=g.current_user.id,
            sender_role="SYSTEM",
            body=(
                "Cảm ơn quý khách đã tin tưởng CINEVO. Chúng tôi đang liên hệ với nhân viên "
                "hỗ trợ. Vui lòng chờ trong giây lát."
            ),
        ))
    db.session.commit()
    return jsonify({"message": message.to_dict()}), 201


@bp.get("/conversation/<int:conversation_id>/messages")
@customer_only
def get_customer_messages(conversation_id):
    conversation = _conversation_for_customer(conversation_id)
    return _messages_response(conversation, staff=False)


@bp.get("/staff/conversations")
@staff_only
def list_staff_conversations():
    status = request.args.get("status", "open")
    if status not in {"open", "closed", "all"}:
        raise ApiError("Trạng thái cuộc trò chuyện không hợp lệ.")
    query = SupportConversation.query
    if status != "all":
        query = query.filter_by(status=status)
    conversations = query.order_by(SupportConversation.updated_at.desc()).limit(200).all()
    result = []
    for conversation in conversations:
        result.append(conversation.to_dict(
            unread_count=_staff_unread_count(conversation),
            latest_message=_latest_message(conversation.id),
        ))
    return jsonify({
        "conversations": result,
        "unread_count": sum(item["unread_count"] for item in result),
        "new_conversations": sum(
            1 for item in result
            if item["status"] == "open"
            and item["unread_count"] > 0
        ),
    })


@bp.post("/staff/conversations/<int:conversation_id>/accept")
@staff_only
def accept_staff_conversation(conversation_id):
    conversation = _conversation_for_staff(conversation_id)
    if conversation.status != "open":
        raise ApiError("Cuộc trò chuyện đã kết thúc.", 409)
    if conversation.assignment:
        if conversation.assignment.staff_id != g.current_user.id:
            raise ApiError("Cuộc trò chuyện đã được một nhân viên khác nhận.", 409, "ALREADY_ASSIGNED")
        return jsonify({"conversation": conversation.to_dict(), "accepted": True})

    assignment = SupportAssignment(
        conversation_id=conversation.id,
        staff_id=g.current_user.id,
    )
    db.session.add(assignment)
    db.session.add(SupportMessage(
        conversation_id=conversation.id,
        sender_id=g.current_user.id,
        sender_role="SYSTEM",
        body=f"Nhân viên {g.current_user.full_name} đã nhận hỗ trợ quý khách.",
    ))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        conversation = _conversation_for_staff(conversation_id)
        if not conversation.assignment:
            raise
        if conversation.assignment.staff_id != g.current_user.id:
            raise ApiError("Cuộc trò chuyện đã được một nhân viên khác nhận.", 409, "ALREADY_ASSIGNED")
    return jsonify({"conversation": conversation.to_dict(), "accepted": True})


@bp.get("/staff/conversations/<int:conversation_id>/messages")
@staff_only
def get_staff_messages(conversation_id):
    conversation = _conversation_for_staff(conversation_id)
    return _messages_response(conversation, staff=True)


@bp.post("/staff/conversations/<int:conversation_id>/messages")
@staff_only
def send_staff_message(conversation_id):
    conversation = _conversation_for_staff(conversation_id)
    if conversation.status != "open":
        raise ApiError("Cuộc trò chuyện đã kết thúc.", 409)
    if not conversation.assignment or conversation.assignment.staff_id != g.current_user.id:
        raise ApiError("Hãy nhận cuộc trò chuyện trước khi trả lời.", 409, "CHAT_NOT_ASSIGNED")
    data = json_body()
    body = clean_str(data.get("body"), "Tin nhắn", min_len=1, max_len=MESSAGE_LIMIT, required=True)
    message = SupportMessage(
        conversation_id=conversation.id,
        sender_id=g.current_user.id,
        sender_role=g.current_user.role.name,
        body=body,
    )
    conversation.updated_at = utc_now()
    db.session.add(message)
    db.session.commit()
    return jsonify({"message": message.to_dict()}), 201


@bp.post("/staff/conversations/<int:conversation_id>/close")
@staff_only
def close_staff_conversation(conversation_id):
    conversation = _conversation_for_staff(conversation_id)
    if (
        conversation.assignment
        and conversation.assignment.staff_id != g.current_user.id
        and g.current_user.role.name != ROLE_ADMIN
    ):
        raise ApiError("Chỉ nhân viên đang phụ trách hoặc quản trị viên mới có thể đóng cuộc trò chuyện.", 403)
    conversation.status = "closed"
    conversation.updated_at = utc_now()
    db.session.commit()
    return jsonify({"conversation": conversation.to_dict(), "closed": True})
