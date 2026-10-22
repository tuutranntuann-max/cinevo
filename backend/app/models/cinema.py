"""Model Cinema (rạp) và Room (phòng chiếu)."""
from ..extensions import db


class Cinema(db.Model):
    __tablename__ = "cinemas"

    id = db.Column(db.Integer, primary_key=True)
    chain = db.Column(db.String(100))
    name = db.Column(db.String(150), nullable=False)
    city = db.Column(db.String(80), nullable=False, index=True)
    address = db.Column(db.String(250))
    phone = db.Column(db.String(20))

    rooms = db.relationship("Room", back_populates="cinema", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "chain": self.chain, "name": self.name, "city": self.city,
                "address": self.address, "phone": self.phone}
