from datetime import date, timedelta
from sqlalchemy.orm import Session
from . import models


def seed_sample_expenses_if_empty(db: Session):
    """Seeds realistic sample expenses only if the expenses table is empty."""
    existing_count = db.query(models.Expense).count()
    if existing_count > 0:
        return

    today = date.today()
    # Helper to calculate relative date
    def days_ago(d: int) -> str:
        return (today - timedelta(days=d)).strftime("%Y-%m-%d")

    sample_data = [
        {
            "amount": 84.50,
            "description": "Weekly grocery store haul",
            "category": "Groceries",
            "date": days_ago(1),
            "payment_method": "Credit Card",
        },
        {
            "amount": 24.00,
            "description": "Lunch with coworker at bistro",
            "category": "Food & Dining",
            "date": days_ago(2),
            "payment_method": "Debit Card",
        },
        {
            "amount": 65.00,
            "description": "High-speed home internet bill",
            "category": "Housing & Utilities",
            "date": days_ago(4),
            "payment_method": "UPI / Bank Transfer",
        },
        {
            "amount": 42.80,
            "description": "Gas station fill-up",
            "category": "Transportation",
            "date": days_ago(6),
            "payment_method": "Credit Card",
        },
        {
            "amount": 16.50,
            "description": "Movie streaming subscription",
            "category": "Entertainment",
            "date": days_ago(10),
            "payment_method": "Credit Card",
        },
        {
            "amount": 115.00,
            "description": "New running sneakers",
            "category": "Shopping",
            "date": days_ago(14),
            "payment_method": "Credit Card",
        },
        {
            "amount": 35.00,
            "description": "Pharmacy vitamins and prescriptions",
            "category": "Healthcare",
            "date": days_ago(18),
            "payment_method": "Cash",
        },
        {
            "amount": 12.75,
            "description": "Artisan coffee and pastries",
            "category": "Food & Dining",
            "date": days_ago(22),
            "payment_method": "UPI / Bank Transfer",
        },
        {
            "amount": 145.20,
            "description": "Monthly electric utility bill",
            "category": "Housing & Utilities",
            "date": days_ago(32),
            "payment_method": "UPI / Bank Transfer",
        },
        {
            "amount": 92.40,
            "description": "Supermarket provisions & cleaning supplies",
            "category": "Groceries",
            "date": days_ago(38),
            "payment_method": "Debit Card",
        },
        {
            "amount": 50.00,
            "description": "Online coding course subscription",
            "category": "Education",
            "date": days_ago(45),
            "payment_method": "Credit Card",
        },
        {
            "amount": 28.00,
            "description": "City train monthly pass recharge",
            "category": "Transportation",
            "date": days_ago(52),
            "payment_method": "Debit Card",
        },
    ]

    for item in sample_data:
        expense = models.Expense(**item)
        db.add(expense)

    db.commit()
    print(f"Successfully seeded {len(sample_data)} sample expenses.")
