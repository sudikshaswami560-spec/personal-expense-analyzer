from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from .database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    payment_method = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Expense id={self.id} amount={self.amount} category='{self.category}' date='{self.date}'>"


class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    month = Column(String(7), unique=True, index=True, nullable=False)  # YYYY-MM
    total_amount = Column(Float, nullable=False)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<MonthlySummary id={self.id} month='{self.month}' total_amount={self.total_amount}>"


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    month = Column(String(7), unique=True, index=True, nullable=False)  # YYYY-MM
    overall_limit = Column(Float, nullable=False)
    category_limits = Column(Text, nullable=True)  # JSON string: {"Groceries": 5000, ...}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Budget id={self.id} month='{self.month}' overall_limit={self.overall_limit}>"


class Income(Base):
    __tablename__ = "incomes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    source = Column(String(100), nullable=False, index=True)  # Salary, Freelance, Business, etc.
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Income id={self.id} amount={self.amount} source='{self.source}' date='{self.date}'>"


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    payment_method = Column(String(50), nullable=False)
    frequency = Column(String(20), nullable=False, default="monthly")  # monthly, weekly, quarterly, yearly
    start_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    next_due_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    status = Column(String(20), nullable=False, default="active", index=True)  # active, paused, stopped
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<RecurringExpense id={self.id} desc='{self.description}' next_due='{self.next_due_date}' status='{self.status}'>"


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, nullable=False, default=0.0)
    target_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    category = Column(String(100), nullable=True)
    notes = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)  # active, completed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SavingsGoal id={self.id} title='{self.title}' target={self.target_amount} current={self.current_amount}>"
