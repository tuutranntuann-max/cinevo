"""Model Product (hàng hóa quản lý tồn kho toàn hệ thống)."""
from ..extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(60), nullable=False, default="Khác")
    description = db.Column(db.String(200))
    price = db.Column(db.Integer, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "category": self.category,
                "description": self.description, "price": self.price,
                "stock_quantity": self.stock_quantity, "active": self.active}
