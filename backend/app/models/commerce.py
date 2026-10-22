from ..extensions import db
from ..timeutil import iso_utc, utc_now


class CommerceSettings(db.Model):
    __tablename__ = "commerce_settings"

    id = db.Column(db.Integer, primary_key=True, default=1)
    values = db.Column(db.JSON, nullable=False, default=dict)


class Membership(db.Model):
    __tablename__ = "memberships"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    tier = db.Column(db.String(20), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    amount = db.Column(db.Integer, nullable=False)
    payment_ref = db.Column(db.String(40), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "tier": self.tier,
            "starts_at": iso_utc(self.starts_at),
            "expires_at": iso_utc(self.expires_at),
            "status": self.status,
            "amount": self.amount,
            "payment_ref": self.payment_ref,
            "created_at": iso_utc(self.created_at),
        }


class ShopOrder(db.Model):
    __tablename__ = "shop_orders"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(24), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subtotal = db.Column(db.Integer, nullable=False)
    discount_amount = db.Column(db.Integer, nullable=False, default=0)
    total_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING")
    pickup_cinema = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    user = db.relationship("User")
    items = db.relationship("ShopOrderItem", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "status": self.status,
            "subtotal": self.subtotal,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount,
            "pickup_cinema": self.pickup_cinema,
            "created_at": iso_utc(self.created_at),
            "items": [
                {"product_id": item.product_id, "name": item.product.name,
                 "quantity": item.quantity, "unit_price": item.unit_price}
                for item in self.items
            ],
        }


class ShopOrderItem(db.Model):
    __tablename__ = "shop_order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("shop_orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)

    product = db.relationship("Product")
