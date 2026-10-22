from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships ensuring all user assets are isolated and cascaded
    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    monthly_summaries = relationship("MonthlySummary", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    incomes = relationship("Income", back_populates="user", cascade="all, delete-orphan")
    recurring_expenses = relationship("RecurringExpense", back_populates="user", cascade="all, delete-orphan")
    savings_goals = relationship("SavingsGoal", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}'>"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    payment_method = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="expenses")

    def __repr__(self):
        return f"<Expense id={self.id} user_id={self.user_id} amount={self.amount} category='{self.category}' date='{self.date}'>"


class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"
    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_user_monthly_summary"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    month = Column(String(7), index=True, nullable=False)  # YYYY-MM
    total_amount = Column(Float, nullable=False)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="monthly_summaries")

    def __repr__(self):
        return f"<MonthlySummary id={self.id} user_id={self.user_id} month='{self.month}' total_amount={self.total_amount}>"


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_user_budget"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    month = Column(String(7), index=True, nullable=False)  # YYYY-MM
    overall_limit = Column(Float, nullable=False)
    category_limits = Column(Text, nullable=True)  # JSON string: {"Groceries": 5000, ...}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="budgets")

    def __repr__(self):
        return f"<Budget id={self.id} user_id={self.user_id} month='{self.month}' overall_limit={self.overall_limit}>"


class Income(Base):
    __tablename__ = "incomes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    source = Column(String(100), nullable=False, index=True)  # Salary, Freelance, Business, etc.
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="incomes")

    def __repr__(self):
        return f"<Income id={self.id} user_id={self.user_id} amount={self.amount} source='{self.source}' date='{self.date}'>"


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    payment_method = Column(String(50), nullable=False)
    frequency = Column(String(20), nullable=False, default="monthly")  # monthly, weekly, quarterly, yearly
    start_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    next_due_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    status = Column(String(20), nullable=False, default="active", index=True)  # active, paused, stopped
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="recurring_expenses")

    def __repr__(self):
        return f"<RecurringExpense id={self.id} user_id={self.user_id} desc='{self.description}' next_due='{self.next_due_date}'>"


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, nullable=False, default=0.0)
    target_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    category = Column(String(100), nullable=True)
    notes = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)  # active, completed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="savings_goals")

    def __repr__(self):
        return f"<SavingsGoal id={self.id} user_id={self.user_id} title='{self.title}' target={self.target_amount}>"
