from ..extensions import db


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    spent_on = db.Column(db.Date, nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "amount": self.amount,
            "spent_on": self.spent_on.isoformat(),
        }
