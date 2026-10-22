"""Model Food (bắp nước / combo)."""
from ..extensions import db


class Food(db.Model):
    __tablename__ = "foods"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Integer, nullable=False)
    is_combo = db.Column(db.Boolean, default=True)
    available = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description,
                "price": self.price, "is_combo": self.is_combo, "available": self.available}
