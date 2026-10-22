from ..extensions import db
from ..timeutil import utc_now


class GmailOAuthCredential(db.Model):
    __tablename__ = "gmail_oauth_credentials"

    id = db.Column(db.Integer, primary_key=True)
    sender_email = db.Column(db.String(254), nullable=False)
    encrypted_tokens = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class GmailAssistantSettings(db.Model):
    __tablename__ = "gmail_assistant_settings"

    id = db.Column(db.Integer, primary_key=True)
    encrypted_settings = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class GmailOAuthState(db.Model):
    __tablename__ = "gmail_oauth_states"

    state_hash = db.Column(db.String(64), primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)
