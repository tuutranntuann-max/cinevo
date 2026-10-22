"""Model roles for customers, employees, managers, and administrators."""
from ..extensions import db

ROLE_USER = "USER"
ROLE_MANAGER = "MANAGER"
ROLE_ADMIN = "ADMIN"
ROLE_EMPLOYEE = "EMPLOYEE"


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(200))

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description}
