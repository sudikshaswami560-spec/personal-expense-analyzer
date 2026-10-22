from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Transportation",
    "Housing & Utilities",
    "Shopping",
    "Entertainment",
    "Healthcare",
    "Education",
    "Personal Care",
    "Other",
]

PAYMENT_METHODS = [
    "UPI",
    "Cash",
    "Credit Card",
    "Debit Card",
    "Bank Transfer",
    "UPI / Bank Transfer",
    "Other",
]


class ExpenseBase(BaseModel):
    amount: float = Field(..., gt=0, description="Expense amount must be greater than 0")
    description: str = Field(..., min_length=1, max_length=255, description="Brief description of the expense")
    category: str = Field(..., description="Category of the expense")
    date: str = Field(..., description="Date of expense in YYYY-MM-DD format")
    payment_method: str = Field(..., description="Method used for payment")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Description cannot be empty or whitespace only")
        return trimmed

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        trimmed = v.strip()
        try:
            # Validate format YYYY-MM-DD
            parsed = datetime.strptime(trimmed, "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be a valid calendar date in YYYY-MM-DD format")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return round(v, 2)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = None
    date: Optional[str] = None
    payment_method: Optional[str] = None

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Description cannot be empty or whitespace only")
            return trimmed
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            try:
                parsed = datetime.strptime(trimmed, "%Y-%m-%d")
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be a valid calendar date in YYYY-MM-DD format")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v <= 0:
                raise ValueError("Amount must be greater than 0")
            return round(v, 2)
        return v


class ExpenseResponse(ExpenseBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MonthlySummaryBase(BaseModel):
    month: str = Field(..., description="Month in YYYY-MM format")
    total_amount: float = Field(..., gt=0, description="Total expense amount must be greater than 0")
    note: Optional[str] = Field(None, max_length=255, description="Optional note or explanation")

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        trimmed = v.strip()
        try:
            parsed = datetime.strptime(trimmed, "%Y-%m")
            return parsed.strftime("%Y-%m")
        except ValueError:
            raise ValueError("Month must be in YYYY-MM format (e.g. 2026-10)")

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Total amount must be greater than 0")
        return round(v, 2)


class MonthlySummaryCreate(MonthlySummaryBase):
    pass


class MonthlySummaryUpdate(BaseModel):
    total_amount: Optional[float] = Field(None, gt=0)
    note: Optional[str] = Field(None, max_length=255)

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v <= 0:
                raise ValueError("Total amount must be greater than 0")
            return round(v, 2)
        return v


class MonthlySummaryResponse(MonthlySummaryBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    itemized_total: Optional[float] = None
    itemized_count: Optional[int] = None

    class Config:
        from_attributes = True


class CategorySummary(BaseModel):
    category: str
    total_amount: float
    percentage: float
    count: int


class MonthlyTrend(BaseModel):
    month: str  # YYYY-MM
    month_name: str  # e.g., "Sep 2026"
    total_amount: float
    count: int
    is_summary: bool = False
    itemized_amount: float = 0.0
    itemized_count: int = 0


class PaymentMethodSummary(BaseModel):
    payment_method: str
    total_amount: float
    percentage: float
    count: int


class AnalyticsSummaryResponse(BaseModel):
    total_spending: float
    total_expenses_count: int
    average_expense: float
    highest_expense: float
    categories: List[CategorySummary]
    monthly_trends: List[MonthlyTrend]
    payment_methods: List[PaymentMethodSummary]
    has_monthly_summary: bool = False
    monthly_summary: Optional[MonthlySummaryResponse] = None
    itemized_spending: Optional[float] = None


class MetadataResponse(BaseModel):
    categories: List[str]
    payment_methods: List[str]
    recorded_months: List[str] = []
    income_sources: List[str] = []


class BulkDeleteRequest(BaseModel):
    ids: List[int] = Field(..., min_length=1, description="List of expense IDs to delete")


class BulkDeleteResponse(BaseModel):
    deleted_count: int
    ids: List[int]
    message: str


class CategoryDelta(BaseModel):
    category: str
    current_amount: float
    previous_amount: float
    delta: float
    percentage_change: float


class PeriodComparisonResponse(BaseModel):
    current_period_label: str
    previous_period_label: str
    current_period_spending: float
    previous_period_spending: float
    difference: float
    percentage_change: float
    current_period_count: int
    previous_period_count: int
    category_deltas: List[CategoryDelta]


# ==========================================
# STAGE 2 SCHEMAS
# ==========================================

INCOME_SOURCES = [
    "Salary",
    "Freelance",
    "Business",
    "Investment",
    "Rental",
    "Gift",
    "Other",
]

RECURRING_FREQUENCIES = ["monthly", "weekly", "quarterly", "yearly"]
RECURRING_STATUSES = ["active", "paused", "stopped"]
SAVINGS_STATUSES = ["active", "completed"]


class BudgetCategoryLimit(BaseModel):
    category: str
    limit: float
    spent: float = 0.0
    remaining: float = 0.0
    percentage: float = 0.0
    status: str = "ok"  # "ok", "warning", "exceeded"


class BudgetCreate(BaseModel):
    month: str = Field(..., description="Month in YYYY-MM format")
    overall_limit: float = Field(..., gt=0, description="Overall monthly budget limit in INR")
    category_limits: Optional[dict[str, float]] = Field(default=None, description="Category-specific limits")

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        trimmed = v.strip()
        try:
            datetime.strptime(trimmed, "%Y-%m")
            return trimmed
        except ValueError:
            raise ValueError("Month must be in YYYY-MM format")


class BudgetResponse(BaseModel):
    id: int
    month: str
    overall_limit: float
    overall_spent: float = 0.0
    overall_remaining: float = 0.0
    overall_percentage: float = 0.0
    overall_status: str = "ok"  # "ok", "warning", "exceeded"
    category_limits: List[BudgetCategoryLimit] = []
    created_at: datetime
    updated_at: datetime


class IncomeBase(BaseModel):
    amount: float = Field(..., gt=0, description="Income amount must be greater than 0")
    source: str = Field(..., description="Source of income (e.g. Salary, Freelance)")
    date: str = Field(..., description="Date of income in YYYY-MM-DD format")
    description: str = Field(..., min_length=1, max_length=255, description="Description of the income")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Description cannot be empty or whitespace only")
        return trimmed

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        trimmed = v.strip()
        try:
            parsed = datetime.strptime(trimmed, "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be a valid calendar date in YYYY-MM-DD format")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return round(v, 2)


class IncomeCreate(IncomeBase):
    pass


class IncomeUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    source: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None


class IncomeResponse(IncomeBase):
    id: int
    created_at: datetime


class IncomeSourceSummary(BaseModel):
    source: str
    total_amount: float
    percentage: float
    count: int


class CashFlowSummaryResponse(BaseModel):
    period_label: str
    total_income: float
    total_expenses: float
    net_balance: float
    savings_rate: float
    income_sources: List[IncomeSourceSummary] = []


class RecurringExpenseBase(BaseModel):
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    description: str = Field(..., min_length=1, max_length=255)
    category: str = Field(...)
    payment_method: str = Field(...)
    frequency: str = Field("monthly", description="Frequency: monthly, weekly, quarterly, yearly")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    next_due_date: str = Field(..., description="Next due date YYYY-MM-DD")
    status: str = Field("active", description="Status: active, paused, stopped")


class RecurringExpenseCreate(RecurringExpenseBase):
    pass


class RecurringExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    next_due_date: Optional[str] = None
    status: Optional[str] = None


class RecurringExpenseResponse(RecurringExpenseBase):
    id: int
    created_at: datetime


class SavingsGoalBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    target_amount: float = Field(..., gt=0, description="Target savings amount in INR")
    current_amount: float = Field(default=0.0, ge=0, description="Current accumulated amount in INR")
    target_date: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    status: str = Field("active", description="Status: active, completed")


class SavingsGoalCreate(SavingsGoalBase):
    pass


class SavingsGoalUpdate(BaseModel):
    title: Optional[str] = None
    target_amount: Optional[float] = Field(None, gt=0)
    current_amount: Optional[float] = Field(None, ge=0)
    target_date: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class SavingsGoalResponse(SavingsGoalBase):
    id: int
    percentage_complete: float = 0.0
    remaining_amount: float = 0.0
    created_at: datetime
    updated_at: datetime


class GoalContributionRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Contribution amount in INR")

