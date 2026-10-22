"""Persistent customer support conversations and messages."""
from sqlalchemy import UniqueConstraint

from ..extensions import db
from ..timeutil import iso_utc, utc_now


class SupportConversation(db.Model):
    __tablename__ = "support_conversations"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now, index=True)
    customer_last_read_message_id = db.Column(db.Integer, nullable=False, default=0)
    staff_last_read_message_id = db.Column(db.Integer, nullable=False, default=0)
    staff_notified = db.Column(db.Boolean, nullable=False, default=False)

    customer = db.relationship("User", foreign_keys=[customer_id])
    assignment = db.relationship("SupportAssignment", back_populates="conversation", uselist=False)
    messages = db.relationship(
        "SupportMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="SupportMessage.id",
    )

    def to_dict(self, *, unread_count=0, latest_message=None):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer_name": self.customer.full_name if self.customer else "Khách hàng",
            "customer_email": self.customer.email if self.customer else "",
            "status": self.status,
            "assigned_staff_id": self.assignment.staff_id if self.assignment else None,
            "assigned_staff_name": (
                self.assignment.staff.full_name if self.assignment and self.assignment.staff else None
            ),
            "unread_count": unread_count,
            "latest_message": latest_message,
            "created_at": iso_utc(self.created_at),
            "updated_at": iso_utc(self.updated_at),
        }


class SupportMessage(db.Model):
    __tablename__ = "support_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("support_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    sender_role = db.Column(db.String(20), nullable=False)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)

    conversation = db.relationship("SupportConversation", back_populates="messages")
    sender = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "sender_name": "CINEVO" if self.sender_role == "SYSTEM" else (
                self.sender.full_name if self.sender else "Người dùng"
            ),
            "sender_role": self.sender_role,
            "body": self.body,
            "created_at": iso_utc(self.created_at),
        }


class SupportAssignment(db.Model):
    __tablename__ = "support_assignments"
    __table_args__ = (UniqueConstraint("conversation_id", name="uq_support_assignment_conversation"),)

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("support_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    accepted_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    conversation = db.relationship("SupportConversation", back_populates="assignment")
    staff = db.relationship("User")
