import json
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from . import models, schemas
from .auth import verify_password, get_password_hash


# ==========================================
# USER AUTHENTICATION & CRUD
# ==========================================

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Retrieve user by normalized email address."""
    clean_email = email.strip().lower()
    return db.query(models.User).filter(models.User.email == clean_email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    """Retrieve user by primary key ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    """Creates a new user with salted bcrypt password hash."""
    clean_email = user_in.email.strip().lower()
    hashed = get_password_hash(user_in.password)
    user = models.User(
        email=clean_email,
        hashed_password=hashed,
        full_name=user_in.full_name.strip() if user_in.full_name else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    """Validates user email and password; returns User if valid, None otherwise."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ==========================================
# EXPENSES CRUD (SCOPED TO USER)
# ==========================================

def get_expenses(
    db: Session,
    user_id: int,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    payment_method: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "date",
    sort_order: str = "desc",
) -> List[models.Expense]:
    """Retrieve expenses strictly belonging to user_id with optional filters."""
    query = db.query(models.Expense).filter(models.Expense.user_id == user_id)

    if month and month.lower() != "all":
        query = query.filter(models.Expense.date.startswith(month))

    if start_date:
        query = query.filter(models.Expense.date >= start_date)

    if end_date:
        query = query.filter(models.Expense.date <= end_date)

    if category and category.lower() != "all":
        query = query.filter(models.Expense.category == category)

    if payment_method and payment_method.lower() != "all":
        if payment_method == "UPI":
            query = query.filter(
                (models.Expense.payment_method == "UPI")
                | (models.Expense.payment_method == "UPI / Bank Transfer")
            )
        elif payment_method == "Bank Transfer":
            query = query.filter(
                (models.Expense.payment_method == "Bank Transfer")
                | (models.Expense.payment_method == "UPI / Bank Transfer")
            )
        else:
            query = query.filter(models.Expense.payment_method == payment_method)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (models.Expense.description.ilike(search_pattern))
            | (models.Expense.category.ilike(search_pattern))
        )

    # Ordering
    sort_column = getattr(models.Expense, sort_by, models.Expense.date)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column), asc(models.Expense.id))
    else:
        query = query.order_by(desc(sort_column), desc(models.Expense.id))

    return query.all()


def get_expense_by_id(db: Session, expense_id: int, user_id: int) -> Optional[models.Expense]:
    """Retrieve a single expense ensuring ownership by user_id."""
    return (
        db.query(models.Expense)
        .filter(models.Expense.id == expense_id, models.Expense.user_id == user_id)
        .first()
    )


def create_expense(
    db: Session, expense_data: schemas.ExpenseCreate, user_id: int
) -> models.Expense:
    """Create a new expense associated with the authenticated user."""
    db_expense = models.Expense(
        user_id=user_id,
        amount=expense_data.amount,
        description=expense_data.description,
        category=expense_data.category,
        date=expense_data.date,
        payment_method=expense_data.payment_method,
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


def update_expense(
    db: Session, expense_id: int, expense_data: schemas.ExpenseUpdate, user_id: int
) -> Optional[models.Expense]:
    """Update an existing expense owned by user_id."""
    db_expense = get_expense_by_id(db, expense_id, user_id=user_id)
    if not db_expense:
        return None

    update_dict = expense_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_expense, field, value)

    db.commit()
    db.refresh(db_expense)
    return db_expense


def delete_expense(db: Session, expense_id: int, user_id: int) -> bool:
    """Delete an expense by ID only if it belongs to user_id."""
    db_expense = get_expense_by_id(db, expense_id, user_id=user_id)
    if not db_expense:
        return False
    db.delete(db_expense)
    db.commit()
    return True


def bulk_delete_expenses(db: Session, ids: List[int], user_id: int) -> int:
    """Delete multiple expenses belonging strictly to user_id."""
    if not ids:
        return 0
    deleted = (
        db.query(models.Expense)
        .filter(models.Expense.id.in_(ids), models.Expense.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


# ==========================================
# MONTHLY SUMMARIES (SCOPED TO USER)
# ==========================================

def get_monthly_summaries(db: Session, user_id: int) -> List[models.MonthlySummary]:
    return (
        db.query(models.MonthlySummary)
        .filter(models.MonthlySummary.user_id == user_id)
        .order_by(desc(models.MonthlySummary.month))
        .all()
    )


def get_monthly_summary_by_month(
    db: Session, month: str, user_id: int
) -> Optional[models.MonthlySummary]:
    return (
        db.query(models.MonthlySummary)
        .filter(models.MonthlySummary.month == month, models.MonthlySummary.user_id == user_id)
        .first()
    )


def upsert_monthly_summary(
    db: Session, summary_data: schemas.MonthlySummaryCreate, user_id: int
) -> models.MonthlySummary:
    existing = get_monthly_summary_by_month(db, summary_data.month, user_id=user_id)
    if existing:
        existing.total_amount = summary_data.total_amount
        if summary_data.note is not None:
            existing.note = summary_data.note
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_summary = models.MonthlySummary(
            user_id=user_id,
            month=summary_data.month,
            total_amount=summary_data.total_amount,
            note=summary_data.note,
        )
        db.add(new_summary)
        db.commit()
        db.refresh(new_summary)
        return new_summary


def delete_monthly_summary(db: Session, month: str, user_id: int) -> bool:
    existing = get_monthly_summary_by_month(db, month, user_id=user_id)
    if not existing:
        return False
    db.delete(existing)
    db.commit()
    return True


# ==========================================
# METADATA & TRENDS (SCOPED TO USER)
# ==========================================

def get_available_months(db: Session, user_id: int) -> List[str]:
    """Returns distinct YYYY-MM strings present in user's expenses and summaries."""
    expense_months = (
        db.query(func.substr(models.Expense.date, 1, 7).label("month"))
        .filter(models.Expense.user_id == user_id)
        .distinct()
        .all()
    )
    summary_months = (
        db.query(models.MonthlySummary.month)
        .filter(models.MonthlySummary.user_id == user_id)
        .distinct()
        .all()
    )
    all_months = set()
    for row in expense_months:
        if row[0]:
            all_months.add(row[0])
    for row in summary_months:
        if row[0]:
            all_months.add(row[0])

    return sorted(list(all_months), reverse=True)


def get_monthly_trends(db: Session, user_id: int) -> List[schemas.MonthlyTrend]:
    """Computes total spending per month for user_id with monthly summary overrides."""
    expense_results = (
        db.query(
            func.substr(models.Expense.date, 1, 7).label("month"),
            func.sum(models.Expense.amount).label("total"),
            func.count(models.Expense.id).label("count"),
        )
        .filter(models.Expense.user_id == user_id)
        .group_by("month")
        .all()
    )
    itemized_map = {}
    for row in expense_results:
        m = row[0]
        if m:
            itemized_map[m] = {
                "total": round(float(row[1] or 0), 2),
                "count": int(row[2] or 0),
            }

    summaries = get_monthly_summaries(db, user_id=user_id)
    summary_map = {s.month: s for s in summaries}

    all_months = sorted(list(set(list(itemized_map.keys()) + list(summary_map.keys()))))

    trends = []
    for month_str in all_months:
        itemized_info = itemized_map.get(month_str, {"total": 0.0, "count": 0})
        summary_rec = summary_map.get(month_str)

        try:
            dt = datetime.strptime(month_str, "%Y-%m")
            month_name = dt.strftime("%b %Y")
        except Exception:
            month_name = month_str

        if summary_rec:
            official_total = round(summary_rec.total_amount, 2)
            is_summary = True
        else:
            official_total = itemized_info["total"]
            is_summary = False

        trends.append(
            schemas.MonthlyTrend(
                month=month_str,
                month_name=month_name,
                total_amount=official_total,
                count=itemized_info["count"],
                is_summary=is_summary,
                itemized_amount=itemized_info["total"],
                itemized_count=itemized_info["count"],
            )
        )

    return trends


def get_analytics_summary(
    db: Session,
    user_id: int,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    payment_method: Optional[str] = None,
) -> schemas.AnalyticsSummaryResponse:
    """Calculates summary statistics scoped strictly to user_id."""
    query = db.query(models.Expense).filter(models.Expense.user_id == user_id)

    has_specific_month = bool(month and month.lower() != "all")
    if has_specific_month:
        query = query.filter(models.Expense.date.startswith(month))

    if start_date:
        query = query.filter(models.Expense.date >= start_date)

    if end_date:
        query = query.filter(models.Expense.date <= end_date)

    has_cat_filter = bool(category and category.lower() != "all")
    if has_cat_filter:
        query = query.filter(models.Expense.category == category)

    has_pm_filter = bool(payment_method and payment_method.lower() != "all")
    if has_pm_filter:
        if payment_method == "UPI":
            query = query.filter(
                (models.Expense.payment_method == "UPI")
                | (models.Expense.payment_method == "UPI / Bank Transfer")
            )
        elif payment_method == "Bank Transfer":
            query = query.filter(
                (models.Expense.payment_method == "Bank Transfer")
                | (models.Expense.payment_method == "UPI / Bank Transfer")
            )
        else:
            query = query.filter(models.Expense.payment_method == payment_method)

    expenses = query.all()

    # Pre-calculate monthly trends for this user
    monthly_trends = get_monthly_trends(db, user_id=user_id)

    # Check for monthly summary override
    monthly_summary_rec = None
    has_monthly_summary = False
    monthly_summary_response = None

    if has_specific_month and not start_date and not end_date and not has_cat_filter and not has_pm_filter:
        monthly_summary_rec = get_monthly_summary_by_month(db, month, user_id=user_id)
        if monthly_summary_rec:
            has_monthly_summary = True
            itemized_sum = round(sum(exp.amount for exp in expenses), 2)
            monthly_summary_response = schemas.MonthlySummaryResponse(
                id=monthly_summary_rec.id,
                user_id=user_id,
                month=monthly_summary_rec.month,
                total_amount=round(monthly_summary_rec.total_amount, 2),
                note=monthly_summary_rec.note,
                created_at=monthly_summary_rec.created_at,
                updated_at=monthly_summary_rec.updated_at,
                itemized_total=itemized_sum,
                itemized_count=len(expenses),
            )

    itemized_spending = round(sum(exp.amount for exp in expenses), 2)

    # Determine official total spending
    if has_monthly_summary and monthly_summary_rec:
        total_spending = round(monthly_summary_rec.total_amount, 2)
        total_count = len(expenses)
        average_expense = round(total_spending / total_count, 2) if total_count > 0 else total_spending
        highest_expense = round(max((exp.amount for exp in expenses), default=total_spending), 2)
    elif not has_specific_month and not start_date and not end_date and not has_cat_filter and not has_pm_filter:
        total_spending = round(sum(t.total_amount for t in monthly_trends), 2)
        total_count = len(expenses)
        average_expense = round(total_spending / total_count, 2) if total_count > 0 else 0.0
        highest_expense = round(max((exp.amount for exp in expenses), default=0.0), 2)
    else:
        total_spending = itemized_spending
        total_count = len(expenses)
        average_expense = round(total_spending / total_count, 2) if total_count > 0 else 0.0
        highest_expense = round(max((exp.amount for exp in expenses), default=0.0), 2)

    # Build Category Breakdown
    cat_dict = {}
    for exp in expenses:
        cat_dict.setdefault(exp.category, {"amount": 0.0, "count": 0})
        cat_dict[exp.category]["amount"] += exp.amount
        cat_dict[exp.category]["count"] += 1

    category_summaries = []
    if has_monthly_summary and monthly_summary_rec and total_spending > itemized_spending:
        remainder = round(total_spending - itemized_spending, 2)
        cat_dict["Uncategorized (Summary Difference)"] = {"amount": remainder, "count": 0}

    for cat_name, data in sorted(cat_dict.items(), key=lambda item: item[1]["amount"], reverse=True):
        amt = round(data["amount"], 2)
        pct = round((amt / total_spending) * 100, 1) if total_spending > 0 else 0.0
        category_summaries.append(
            schemas.CategorySummary(
                category=cat_name,
                total_amount=amt,
                percentage=pct,
                count=data["count"],
            )
        )

    # Build Payment Method Breakdown
    pm_dict = {}
    for exp in expenses:
        pm = exp.payment_method
        pm_dict.setdefault(pm, {"amount": 0.0, "count": 0})
        pm_dict[pm]["amount"] += exp.amount
        pm_dict[pm]["count"] += 1

    payment_summaries = []
    for pm_name, data in sorted(pm_dict.items(), key=lambda item: item[1]["amount"], reverse=True):
        amt = round(data["amount"], 2)
        pct = round((amt / itemized_spending) * 100, 1) if itemized_spending > 0 else 0.0
        payment_summaries.append(
            schemas.PaymentMethodSummary(
                payment_method=pm_name,
                total_amount=amt,
                percentage=pct,
                count=data["count"],
            )
        )

    return schemas.AnalyticsSummaryResponse(
        total_spending=total_spending,
        total_expenses_count=total_count,
        average_expense=average_expense,
        highest_expense=highest_expense,
        categories=category_summaries,
        monthly_trends=monthly_trends,
        payment_methods=payment_summaries,
        has_monthly_summary=has_monthly_summary,
        monthly_summary=monthly_summary_response,
        itemized_spending=itemized_spending,
    )


def get_period_comparison(
    db: Session,
    user_id: int,
    current_start: str,
    current_end: str,
    prev_start: str,
    prev_end: str,
    current_label: str = "Current Period",
    prev_label: str = "Previous Period",
) -> schemas.PeriodComparisonResponse:
    """Compares spending between two distinct date periods for user_id."""
    curr_expenses = (
        db.query(models.Expense)
        .filter(
            models.Expense.user_id == user_id,
            models.Expense.date >= current_start,
            models.Expense.date <= current_end,
        )
        .all()
    )
    prev_expenses = (
        db.query(models.Expense)
        .filter(
            models.Expense.user_id == user_id,
            models.Expense.date >= prev_start,
            models.Expense.date <= prev_end,
        )
        .all()
    )

    curr_total = round(sum(e.amount for e in curr_expenses), 2)
    prev_total = round(sum(e.amount for e in prev_expenses), 2)
    diff = round(curr_total - prev_total, 2)
    if prev_total > 0:
        pct_change = round(((curr_total - prev_total) / prev_total) * 100, 1)
    elif curr_total > 0:
        pct_change = 100.0
    else:
        pct_change = 0.0

    curr_cat = {}
    for e in curr_expenses:
        curr_cat[e.category] = curr_cat.get(e.category, 0.0) + e.amount

    prev_cat = {}
    for e in prev_expenses:
        prev_cat[e.category] = prev_cat.get(e.category, 0.0) + e.amount

    all_cats = sorted(list(set(list(curr_cat.keys()) + list(prev_cat.keys()))))
    cat_deltas = []
    for c in all_cats:
        c_amt = round(curr_cat.get(c, 0.0), 2)
        p_amt = round(prev_cat.get(c, 0.0), 2)
        d = round(c_amt - p_amt, 2)
        if p_amt > 0:
            c_pct = round(((c_amt - p_amt) / p_amt) * 100, 1)
        elif c_amt > 0:
            c_pct = 100.0
        else:
            c_pct = 0.0
        cat_deltas.append(
            schemas.CategoryDelta(
                category=c,
                current_amount=c_amt,
                previous_amount=p_amt,
                delta=d,
                percentage_change=c_pct,
            )
        )

    cat_deltas.sort(key=lambda x: abs(x.delta), reverse=True)

    return schemas.PeriodComparisonResponse(
        current_period_label=current_label,
        previous_period_label=prev_label,
        current_period_spending=curr_total,
        previous_period_spending=prev_total,
        difference=diff,
        percentage_change=pct_change,
        current_period_count=len(curr_expenses),
        previous_period_count=len(prev_expenses),
        category_deltas=cat_deltas,
    )


# ==========================================
# BUDGETS CRUD (SCOPED TO USER)
# ==========================================

def get_budget_by_month(db: Session, month: str, user_id: int) -> Optional[models.Budget]:
    return (
        db.query(models.Budget)
        .filter(models.Budget.month == month, models.Budget.user_id == user_id)
        .first()
    )


def get_budgets(db: Session, user_id: int) -> List[models.Budget]:
    return (
        db.query(models.Budget)
        .filter(models.Budget.user_id == user_id)
        .order_by(desc(models.Budget.month))
        .all()
    )


def upsert_budget(
    db: Session, budget_in: schemas.BudgetCreate, user_id: int
) -> models.Budget:
    existing = get_budget_by_month(db, budget_in.month, user_id=user_id)
    cat_limits_json = json.dumps(budget_in.category_limits or {})

    if existing:
        existing.overall_limit = budget_in.overall_limit
        existing.category_limits = cat_limits_json
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_b = models.Budget(
            user_id=user_id,
            month=budget_in.month,
            overall_limit=budget_in.overall_limit,
            category_limits=cat_limits_json,
        )
        db.add(new_b)
        db.commit()
        db.refresh(new_b)
        return new_b


def delete_budget(db: Session, month: str, user_id: int) -> bool:
    existing = get_budget_by_month(db, month, user_id=user_id)
    if not existing:
        return False
    db.delete(existing)
    db.commit()
    return True


def build_budget_response(
    db: Session, budget: models.Budget, user_id: int
) -> schemas.BudgetResponse:
    expenses = get_expenses(db, user_id=user_id, month=budget.month)
    total_spent = round(sum(e.amount for e in expenses), 2)
    overall_pct = (
        round((total_spent / budget.overall_limit) * 100, 1)
        if budget.overall_limit > 0
        else 0.0
    )

    overall_status = "exceeded" if total_spent > budget.overall_limit else ("warning" if overall_pct >= 85 else "ok")

    limits_dict = {}
    if budget.category_limits:
        try:
            limits_dict = json.loads(budget.category_limits)
        except Exception:
            limits_dict = {}

    cat_spending = {}
    for e in expenses:
        cat_spending[e.category] = cat_spending.get(e.category, 0.0) + e.amount

    category_progress_list = []
    for cat, limit in limits_dict.items():
        spent = round(cat_spending.get(cat, 0.0), 2)
        pct = round((spent / limit) * 100, 1) if limit > 0 else 0.0
        rem = round(limit - spent, 2)
        cat_status = "exceeded" if spent > limit else ("warning" if pct >= 85 else "ok")
        category_progress_list.append(
            schemas.BudgetCategoryLimit(
                category=cat,
                limit=limit,
                spent=spent,
                remaining=rem,
                percentage=pct,
                status=cat_status,
            )
        )

    return schemas.BudgetResponse(
        id=budget.id,
        user_id=user_id,
        month=budget.month,
        overall_limit=budget.overall_limit,
        overall_spent=total_spent,
        overall_remaining=round(budget.overall_limit - total_spent, 2),
        overall_percentage=overall_pct,
        overall_status=overall_status,
        category_limits=category_progress_list,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


# ==========================================
# INCOME CRUD (SCOPED TO USER)
# ==========================================

def get_incomes(
    db: Session,
    user_id: int,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: Optional[str] = None,
) -> List[models.Income]:
    query = db.query(models.Income).filter(models.Income.user_id == user_id)
    if month and month.lower() != "all":
        query = query.filter(models.Income.date.startswith(month))
    if start_date:
        query = query.filter(models.Income.date >= start_date)
    if end_date:
        query = query.filter(models.Income.date <= end_date)
    if source and source.lower() != "all":
        query = query.filter(models.Income.source == source)
    return query.order_by(desc(models.Income.date)).all()


def get_income_by_id(db: Session, income_id: int, user_id: int) -> Optional[models.Income]:
    return (
        db.query(models.Income)
        .filter(models.Income.id == income_id, models.Income.user_id == user_id)
        .first()
    )


def create_income(
    db: Session, income_in: schemas.IncomeCreate, user_id: int
) -> models.Income:
    income = models.Income(
        user_id=user_id,
        amount=income_in.amount,
        source=income_in.source,
        date=income_in.date,
        description=income_in.description,
    )
    db.add(income)
    db.commit()
    db.refresh(income)
    return income


def update_income(
    db: Session, income_id: int, income_in: schemas.IncomeUpdate, user_id: int
) -> Optional[models.Income]:
    income = get_income_by_id(db, income_id, user_id=user_id)
    if not income:
        return None
    for field, val in income_in.model_dump(exclude_unset=True).items():
        setattr(income, field, val)
    db.commit()
    db.refresh(income)
    return income


def delete_income(db: Session, income_id: int, user_id: int) -> bool:
    income = get_income_by_id(db, income_id, user_id=user_id)
    if not income:
        return False
    db.delete(income)
    db.commit()
    return True


def get_cash_flow_summary(
    db: Session,
    user_id: int,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> schemas.CashFlowSummaryResponse:
    incomes = get_incomes(db, user_id=user_id, month=month, start_date=start_date, end_date=end_date)
    expenses = get_expenses(db, user_id=user_id, month=month, start_date=start_date, end_date=end_date)

    tot_income = round(sum(i.amount for i in incomes), 2)
    tot_expenses = round(sum(e.amount for e in expenses), 2)
    net_bal = round(tot_income - tot_expenses, 2)
    savings_rate = round((net_bal / tot_income) * 100, 1) if tot_income > 0 else 0.0

    # Source breakdown
    src_map = {}
    for i in incomes:
        if i.source not in src_map:
            src_map[i.source] = {"amount": 0.0, "count": 0}
        src_map[i.source]["amount"] += i.amount
        src_map[i.source]["count"] += 1

    sources = [
        schemas.IncomeSourceSummary(
            source=s,
            total_amount=round(data["amount"], 2),
            percentage=round((data["amount"] / tot_income) * 100, 1) if tot_income > 0 else 0.0,
            count=data["count"],
        )
        for s, data in src_map.items()
    ]

    label = month or (f"{start_date} to {end_date}" if start_date and end_date else "All Time")
    return schemas.CashFlowSummaryResponse(
        period_label=label,
        total_income=tot_income,
        total_expenses=tot_expenses,
        net_balance=net_bal,
        savings_rate=savings_rate,
        income_sources=sources,
    )


# ==========================================
# RECURRING EXPENSES CRUD (SCOPED TO USER)
# ==========================================

def get_recurring_expenses(
    db: Session, user_id: int, status: Optional[str] = None
) -> List[models.RecurringExpense]:
    query = db.query(models.RecurringExpense).filter(models.RecurringExpense.user_id == user_id)
    if status and status.lower() != "all":
        query = query.filter(models.RecurringExpense.status == status)
    return query.order_by(asc(models.RecurringExpense.next_due_date)).all()


def get_recurring_expense_by_id(
    db: Session, recurring_id: int, user_id: int
) -> Optional[models.RecurringExpense]:
    return (
        db.query(models.RecurringExpense)
        .filter(
            models.RecurringExpense.id == recurring_id,
            models.RecurringExpense.user_id == user_id,
        )
        .first()
    )


def create_recurring_expense(
    db: Session, rec_in: schemas.RecurringExpenseCreate, user_id: int
) -> models.RecurringExpense:
    rec = models.RecurringExpense(
        user_id=user_id,
        amount=rec_in.amount,
        description=rec_in.description,
        category=rec_in.category,
        payment_method=rec_in.payment_method,
        frequency=rec_in.frequency,
        start_date=rec_in.start_date,
        next_due_date=rec_in.next_due_date,
        status=rec_in.status,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def update_recurring_expense(
    db: Session,
    recurring_id: int,
    rec_in: schemas.RecurringExpenseUpdate,
    user_id: int,
) -> Optional[models.RecurringExpense]:
    rec = get_recurring_expense_by_id(db, recurring_id, user_id=user_id)
    if not rec:
        return None
    for field, val in rec_in.model_dump(exclude_unset=True).items():
        setattr(rec, field, val)
    db.commit()
    db.refresh(rec)
    return rec


def delete_recurring_expense(db: Session, recurring_id: int, user_id: int) -> bool:
    rec = get_recurring_expense_by_id(db, recurring_id, user_id=user_id)
    if not rec:
        return False
    db.delete(rec)
    db.commit()
    return True


def toggle_recurring_status(
    db: Session, recurring_id: int, new_status: str, user_id: int
) -> Optional[models.RecurringExpense]:
    rec = get_recurring_expense_by_id(db, recurring_id, user_id=user_id)
    if not rec:
        return None
    rec.status = new_status
    db.commit()
    db.refresh(rec)
    return rec


def advance_due_date(current_due_str: str, frequency: str) -> str:
    try:
        dt = datetime.strptime(current_due_str, "%Y-%m-%d")
        freq = frequency.lower()
        if freq == "weekly":
            next_dt = dt + timedelta(days=7)
        elif freq == "quarterly":
            month = dt.month + 3
            year = dt.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            day = min(dt.day, 28)
            next_dt = datetime(year, month, day)
        elif freq == "yearly":
            next_dt = datetime(dt.year + 1, dt.month, min(dt.day, 28))
        else:  # monthly default
            month = dt.month + 1
            year = dt.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            day = min(dt.day, 28)
            next_dt = datetime(year, month, day)
        return next_dt.strftime("%Y-%m-%d")
    except Exception:
        return current_due_str


def record_due_expense(
    db: Session, recurring_id: int, user_id: int
) -> Tuple[Optional[models.Expense], Optional[models.RecurringExpense]]:
    rec = get_recurring_expense_by_id(db, recurring_id, user_id=user_id)
    if not rec:
        return None, None

    expense = models.Expense(
        user_id=user_id,
        amount=rec.amount,
        description=f"{rec.description} (Auto)",
        category=rec.category,
        payment_method=rec.payment_method,
        date=rec.next_due_date,
    )
    db.add(expense)
    rec.next_due_date = advance_due_date(rec.next_due_date, rec.frequency)
    db.commit()
    db.refresh(expense)
    db.refresh(rec)
    return expense, rec


# ==========================================
# SAVINGS GOALS CRUD (SCOPED TO USER)
# ==========================================

def get_savings_goals(
    db: Session, user_id: int, status: Optional[str] = None
) -> List[models.SavingsGoal]:
    query = db.query(models.SavingsGoal).filter(models.SavingsGoal.user_id == user_id)
    if status and status.lower() != "all":
        query = query.filter(models.SavingsGoal.status == status)
    return query.order_by(asc(models.SavingsGoal.target_date)).all()


def get_savings_goal_by_id(
    db: Session, goal_id: int, user_id: int
) -> Optional[models.SavingsGoal]:
    return (
        db.query(models.SavingsGoal)
        .filter(models.SavingsGoal.id == goal_id, models.SavingsGoal.user_id == user_id)
        .first()
    )


def create_savings_goal(
    db: Session, goal_in: schemas.SavingsGoalCreate, user_id: int
) -> models.SavingsGoal:
    goal = models.SavingsGoal(
        user_id=user_id,
        title=goal_in.title,
        target_amount=goal_in.target_amount,
        current_amount=goal_in.current_amount,
        target_date=goal_in.target_date,
        category=goal_in.category,
        notes=goal_in.notes,
        status=goal_in.status,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_savings_goal(
    db: Session, goal_id: int, goal_in: schemas.SavingsGoalUpdate, user_id: int
) -> Optional[models.SavingsGoal]:
    goal = get_savings_goal_by_id(db, goal_id, user_id=user_id)
    if not goal:
        return None
    for field, val in goal_in.model_dump(exclude_unset=True).items():
        setattr(goal, field, val)
    goal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(goal)
    return goal


def delete_savings_goal(db: Session, goal_id: int, user_id: int) -> bool:
    goal = get_savings_goal_by_id(db, goal_id, user_id=user_id)
    if not goal:
        return False
    db.delete(goal)
    db.commit()
    return True


def contribute_to_goal(
    db: Session, goal_id: int, amount: float, user_id: int
) -> Optional[models.SavingsGoal]:
    goal = get_savings_goal_by_id(db, goal_id, user_id=user_id)
    if not goal:
        return None
    goal.current_amount = round(goal.current_amount + amount, 2)
    if goal.current_amount >= goal.target_amount:
        goal.status = "completed"
    goal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(goal)
    return goal


def build_savings_goal_response(goal: models.SavingsGoal) -> schemas.SavingsGoalResponse:
    pct = (
        round((goal.current_amount / goal.target_amount) * 100, 1)
        if goal.target_amount > 0
        else 0.0
    )
    rem = max(0.0, round(goal.target_amount - goal.current_amount, 2))
    return schemas.SavingsGoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        title=goal.title,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        category=goal.category,
        notes=goal.notes,
        status=goal.status,
        percentage_complete=min(pct, 100.0),
        remaining_amount=rem,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )
