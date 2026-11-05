from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class CalculationHistory(db.Model):
    __tablename__ = "calculation_history"

    id = db.Column(db.Integer, primary_key=True)
    input_expression = db.Column(db.Text, nullable=False)
    result = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    calculator_type = db.Column(db.String(80), nullable=False, index=True)
    purpose = db.Column(db.String(240), nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
