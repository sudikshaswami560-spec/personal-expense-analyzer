import json
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from . import models, schemas


def get_expenses(
    db: Session,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    payment_method: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "date",
    sort_order: str = "desc",
) -> List[models.Expense]:
    query = db.query(models.Expense)

    if month and month.lower() != "all":
        query = query.filter(models.Expense.date.startswith(month))

    if start_date:
        query = query.filter(models.Expense.date >= start_date)

    if end_date:
        query = query.filter(models.Expense.date <= end_date)

    if category and category.lower() != "all":
        query = query.filter(models.Expense.category == category)

    if payment_method and payment_method.lower() != "all":
        # Handle UPI / Bank Transfer matching or specific
        if payment_method == "UPI":
            query = query.filter((models.Expense.payment_method == "UPI") | (models.Expense.payment_method == "UPI / Bank Transfer"))
        elif payment_method == "Bank Transfer":
            query = query.filter((models.Expense.payment_method == "Bank Transfer") | (models.Expense.payment_method == "UPI / Bank Transfer"))
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


def get_expense_by_id(db: Session, expense_id: int) -> Optional[models.Expense]:
    return db.query(models.Expense).filter(models.Expense.id == expense_id).first()


def create_expense(db: Session, expense_data: schemas.ExpenseCreate) -> models.Expense:
    db_expense = models.Expense(
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
    db: Session, expense_id: int, expense_data: schemas.ExpenseUpdate
) -> Optional[models.Expense]:
    db_expense = get_expense_by_id(db, expense_id)
    if not db_expense:
        return None

    update_dict = expense_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_expense, field, value)

    db.commit()
    db.refresh(db_expense)
    return db_expense


def delete_expense(db: Session, expense_id: int) -> bool:
    db_expense = get_expense_by_id(db, expense_id)
    if not db_expense:
        return False
    db.delete(db_expense)
    db.commit()
    return True


def bulk_delete_expenses(db: Session, ids: List[int]) -> int:
    if not ids:
        return 0
    deleted = db.query(models.Expense).filter(models.Expense.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return deleted


def get_monthly_summaries(db: Session) -> List[models.MonthlySummary]:
    return db.query(models.MonthlySummary).order_by(desc(models.MonthlySummary.month)).all()


def get_monthly_summary_by_month(db: Session, month: str) -> Optional[models.MonthlySummary]:
    return db.query(models.MonthlySummary).filter(models.MonthlySummary.month == month).first()


def upsert_monthly_summary(
    db: Session, summary_data: schemas.MonthlySummaryCreate
) -> models.MonthlySummary:
    existing = get_monthly_summary_by_month(db, summary_data.month)
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
            month=summary_data.month,
            total_amount=summary_data.total_amount,
            note=summary_data.note,
        )
        db.add(new_summary)
        db.commit()
        db.refresh(new_summary)
        return new_summary


def delete_monthly_summary(db: Session, month: str) -> bool:
    existing = get_monthly_summary_by_month(db, month)
    if not existing:
        return False
    db.delete(existing)
    db.commit()
    return True


def get_available_months(db: Session) -> List[str]:
    """Returns distinct YYYY-MM strings present in expenses and monthly summaries, sorted descending."""
    expense_months = (
        db.query(func.substr(models.Expense.date, 1, 7).label("month"))
        .distinct()
        .all()
    )
    summary_months = (
        db.query(models.MonthlySummary.month)
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


def get_monthly_trends(db: Session) -> List[schemas.MonthlyTrend]:
    """
    Computes total spending per month across the database.
    If a MonthlySummary exists for a month, it is treated as that month's overall total
    to avoid double-counting, while itemized metrics are preserved.
    """
    # 1. Fetch itemized stats by month
    expense_results = (
        db.query(
            func.substr(models.Expense.date, 1, 7).label("month"),
            func.sum(models.Expense.amount).label("total"),
            func.count(models.Expense.id).label("count"),
        )
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

    # 2. Fetch all monthly summaries
    summaries = get_monthly_summaries(db)
    summary_map = {s.month: s for s in summaries}

    # 3. Combine distinct months
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
            # Monthly summary overrides itemized total to prevent double-counting
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
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    payment_method: Optional[str] = None,
) -> schemas.AnalyticsSummaryResponse:
    query = db.query(models.Expense)

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
            query = query.filter((models.Expense.payment_method == "UPI") | (models.Expense.payment_method == "UPI / Bank Transfer"))
        elif payment_method == "Bank Transfer":
            query = query.filter((models.Expense.payment_method == "Bank Transfer") | (models.Expense.payment_method == "UPI / Bank Transfer"))
        else:
            query = query.filter(models.Expense.payment_method == payment_method)

    expenses = query.all()

    # Pre-calculate monthly trends across entire history
    monthly_trends = get_monthly_trends(db)

    # Check for monthly summary override
    monthly_summary_rec = None
    has_monthly_summary = False
    monthly_summary_response = None

    if has_specific_month and not start_date and not end_date and not has_cat_filter and not has_pm_filter:
        monthly_summary_rec = get_monthly_summary_by_month(db, month)
        if monthly_summary_rec:
            has_monthly_summary = True
            itemized_sum = round(sum(exp.amount for exp in expenses), 2)
            monthly_summary_response = schemas.MonthlySummaryResponse(
                id=monthly_summary_rec.id,
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
        # Override with Monthly Summary
        total_spending = round(monthly_summary_rec.total_amount, 2)
        total_count = len(expenses)
        average_expense = round(total_spending / total_count, 2) if total_count > 0 else total_spending
        highest_expense = round(max((exp.amount for exp in expenses), default=total_spending), 2)
    elif not has_specific_month and not start_date and not end_date and not has_cat_filter and not has_pm_filter:
        # For "All Months" with no category/payment filter: sum of official monthly totals
        total_spending = round(sum(t.total_amount for t in monthly_trends), 2)
        total_count = len(expenses)
        average_expense = round(total_spending / total_count, 2) if total_count > 0 else 0.0
        highest_expense = round(max((exp.amount for exp in expenses), default=0.0), 2)
    else:
        # Filtered by category, payment method, or custom date range
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

    # If Monthly Summary is active and greater than itemized sum, account for remainder
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
        # Normalize UPI and Bank Transfer grouping
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
    current_start: str,
    current_end: str,
    prev_start: str,
    prev_end: str,
    current_label: str = "Current Period",
    prev_label: str = "Previous Period",
) -> schemas.PeriodComparisonResponse:
    """Compares spending between two distinct date periods."""
    curr_expenses = (
        db.query(models.Expense)
        .filter(models.Expense.date >= current_start, models.Expense.date <= current_end)
        .all()
    )
    prev_expenses = (
        db.query(models.Expense)
        .filter(models.Expense.date >= prev_start, models.Expense.date <= prev_end)
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

    # Category comparison
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
# STAGE 2: BUDGETS CRUD
# ==========================================

def get_budget_by_month(db: Session, month: str) -> Optional[models.Budget]:
    return db.query(models.Budget).filter(models.Budget.month == month).first()


def get_budgets(db: Session) -> List[models.Budget]:
    return db.query(models.Budget).order_by(desc(models.Budget.month)).all()


def upsert_budget(db: Session, budget_in: schemas.BudgetCreate) -> models.Budget:
    existing = get_budget_by_month(db, budget_in.month)
    cat_limits_json = json.dumps(budget_in.category_limits or {})

    if existing:
        existing.overall_limit = budget_in.overall_limit
        existing.category_limits = cat_limits_json
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_budget = models.Budget(
            month=budget_in.month,
            overall_limit=budget_in.overall_limit,
            category_limits=cat_limits_json,
        )
        db.add(new_budget)
        db.commit()
        db.refresh(new_budget)
        return new_budget


def delete_budget(db: Session, month: str) -> bool:
    existing = get_budget_by_month(db, month)
    if not existing:
        return False
    db.delete(existing)
    db.commit()
    return True


def build_budget_response(db: Session, budget: models.Budget) -> schemas.BudgetResponse:
    # 1. Calculate actual spending in that month (using monthly summary override if present)
    ms = get_monthly_summary_by_month(db, budget.month)
    expenses = get_expenses(db, month=budget.month)
    itemized_spent = round(sum(e.amount for e in expenses), 2)
    overall_spent = ms.total_amount if ms else itemized_spent

    overall_remaining = round(budget.overall_limit - overall_spent, 2)
    overall_pct = (
        round((overall_spent / budget.overall_limit) * 100, 1)
        if budget.overall_limit > 0
        else 0.0
    )

    if overall_pct >= 100.0:
        overall_status = "exceeded"
    elif overall_pct >= 80.0:
        overall_status = "warning"
    else:
        overall_status = "ok"

    # Category breakdown
    cat_limits_raw = {}
    if budget.category_limits:
        try:
            cat_limits_raw = json.loads(budget.category_limits)
        except Exception:
            cat_limits_raw = {}

    cat_spent_map = {}
    for exp in expenses:
        cat_spent_map[exp.category] = cat_spent_map.get(exp.category, 0.0) + exp.amount

    category_limits_list = []
    for cat_name, limit_val in cat_limits_raw.items():
        if limit_val and float(limit_val) > 0:
            limit_float = round(float(limit_val), 2)
            c_spent = round(cat_spent_map.get(cat_name, 0.0), 2)
            c_remaining = round(limit_float - c_spent, 2)
            c_pct = round((c_spent / limit_float) * 100, 1)
            if c_pct >= 100.0:
                c_status = "exceeded"
            elif c_pct >= 80.0:
                c_status = "warning"
            else:
                c_status = "ok"

            category_limits_list.append(
                schemas.BudgetCategoryLimit(
                    category=cat_name,
                    limit=limit_float,
                    spent=c_spent,
                    remaining=c_remaining,
                    percentage=c_pct,
                    status=c_status,
                )
            )

    return schemas.BudgetResponse(
        id=budget.id,
        month=budget.month,
        overall_limit=budget.overall_limit,
        overall_spent=overall_spent,
        overall_remaining=overall_remaining,
        overall_percentage=overall_pct,
        overall_status=overall_status,
        category_limits=category_limits_list,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


# ==========================================
# STAGE 2: INCOME CRUD
# ==========================================

def get_incomes(
    db: Session,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: Optional[str] = None,
) -> List[models.Income]:
    query = db.query(models.Income)
    if month and month.lower() != "all":
        query = query.filter(models.Income.date.startswith(month))
    if start_date:
        query = query.filter(models.Income.date >= start_date)
    if end_date:
        query = query.filter(models.Income.date <= end_date)
    if source and source.lower() != "all":
        query = query.filter(models.Income.source == source)

    return query.order_by(desc(models.Income.date), desc(models.Income.id)).all()


def get_income_by_id(db: Session, income_id: int) -> Optional[models.Income]:
    return db.query(models.Income).filter(models.Income.id == income_id).first()


def create_income(db: Session, income_in: schemas.IncomeCreate) -> models.Income:
    rec = models.Income(
        amount=income_in.amount,
        source=income_in.source,
        date=income_in.date,
        description=income_in.description,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def update_income(
    db: Session, income_id: int, income_in: schemas.IncomeUpdate
) -> Optional[models.Income]:
    rec = get_income_by_id(db, income_id)
    if not rec:
        return None
    if income_in.amount is not None:
        rec.amount = income_in.amount
    if income_in.source is not None:
        rec.source = income_in.source
    if income_in.date is not None:
        rec.date = income_in.date
    if income_in.description is not None:
        rec.description = income_in.description
    db.commit()
    db.refresh(rec)
    return rec


def delete_income(db: Session, income_id: int) -> bool:
    rec = get_income_by_id(db, income_id)
    if not rec:
        return False
    db.delete(rec)
    db.commit()
    return True


def get_cash_flow_summary(
    db: Session,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> schemas.CashFlowSummaryResponse:
    incomes = get_incomes(db, month=month, start_date=start_date, end_date=end_date)
    total_income = round(sum(i.amount for i in incomes), 2)

    expenses_summary = get_analytics_summary(
        db, month=month, start_date=start_date, end_date=end_date
    )
    total_expenses = expenses_summary.total_spending

    net_balance = round(total_income - total_expenses, 2)
    savings_rate = (
        round((net_balance / total_income) * 100, 1) if total_income > 0 else 0.0
    )

    source_map = {}
    for inc in incomes:
        source_map.setdefault(inc.source, {"amount": 0.0, "count": 0})
        source_map[inc.source]["amount"] += inc.amount
        source_map[inc.source]["count"] += 1

    source_summaries = []
    for s_name, s_data in sorted(
        source_map.items(), key=lambda x: x[1]["amount"], reverse=True
    ):
        s_amt = round(s_data["amount"], 2)
        s_pct = round((s_amt / total_income) * 100, 1) if total_income > 0 else 0.0
        source_summaries.append(
            schemas.IncomeSourceSummary(
                source=s_name,
                total_amount=s_amt,
                percentage=s_pct,
                count=s_data["count"],
            )
        )

    period_str = month or (
        f"{start_date} to {end_date}" if start_date and end_date else "All Time"
    )

    return schemas.CashFlowSummaryResponse(
        period_label=period_str,
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        savings_rate=savings_rate,
        income_sources=source_summaries,
    )


# ==========================================
# STAGE 2: RECURRING EXPENSES CRUD
# ==========================================

def get_recurring_expenses(
    db: Session, status: Optional[str] = None
) -> List[models.RecurringExpense]:
    query = db.query(models.RecurringExpense)
    if status and status.lower() != "all":
        query = query.filter(models.RecurringExpense.status == status)
    return query.order_by(asc(models.RecurringExpense.next_due_date)).all()


def get_recurring_expense_by_id(
    db: Session, recurring_id: int
) -> Optional[models.RecurringExpense]:
    return (
        db.query(models.RecurringExpense)
        .filter(models.RecurringExpense.id == recurring_id)
        .first()
    )


def create_recurring_expense(
    db: Session, rec_in: schemas.RecurringExpenseCreate
) -> models.RecurringExpense:
    rec = models.RecurringExpense(
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
    db: Session, recurring_id: int, rec_in: schemas.RecurringExpenseUpdate
) -> Optional[models.RecurringExpense]:
    rec = get_recurring_expense_by_id(db, recurring_id)
    if not rec:
        return None
    for field, val in rec_in.model_dump(exclude_unset=True).items():
        setattr(rec, field, val)
    db.commit()
    db.refresh(rec)
    return rec


def delete_recurring_expense(db: Session, recurring_id: int) -> bool:
    rec = get_recurring_expense_by_id(db, recurring_id)
    if not rec:
        return False
    db.delete(rec)
    db.commit()
    return True


def toggle_recurring_status(
    db: Session, recurring_id: int, new_status: str
) -> Optional[models.RecurringExpense]:
    rec = get_recurring_expense_by_id(db, recurring_id)
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
    db: Session, recurring_id: int
) -> Tuple[Optional[models.Expense], Optional[models.RecurringExpense]]:
    rec = get_recurring_expense_by_id(db, recurring_id)
    if not rec:
        return None, None

    # Create actual itemized expense
    expense = models.Expense(
        amount=rec.amount,
        description=f"{rec.description} (Auto)",
        category=rec.category,
        payment_method=rec.payment_method,
        date=rec.next_due_date,
    )
    db.add(expense)

    # Advance next due date
    rec.next_due_date = advance_due_date(rec.next_due_date, rec.frequency)

    db.commit()
    db.refresh(expense)
    db.refresh(rec)
    return expense, rec


# ==========================================
# STAGE 2: SAVINGS GOALS CRUD
# ==========================================

def get_savings_goals(
    db: Session, status: Optional[str] = None
) -> List[models.SavingsGoal]:
    query = db.query(models.SavingsGoal)
    if status and status.lower() != "all":
        query = query.filter(models.SavingsGoal.status == status)
    return query.order_by(asc(models.SavingsGoal.target_date)).all()


def get_savings_goal_by_id(db: Session, goal_id: int) -> Optional[models.SavingsGoal]:
    return db.query(models.SavingsGoal).filter(models.SavingsGoal.id == goal_id).first()


def create_savings_goal(
    db: Session, goal_in: schemas.SavingsGoalCreate
) -> models.SavingsGoal:
    goal = models.SavingsGoal(
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
    db: Session, goal_id: int, goal_in: schemas.SavingsGoalUpdate
) -> Optional[models.SavingsGoal]:
    goal = get_savings_goal_by_id(db, goal_id)
    if not goal:
        return None
    for field, val in goal_in.model_dump(exclude_unset=True).items():
        setattr(goal, field, val)
    goal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(goal)
    return goal


def delete_savings_goal(db: Session, goal_id: int) -> bool:
    goal = get_savings_goal_by_id(db, goal_id)
    if not goal:
        return False
    db.delete(goal)
    db.commit()
    return True


def contribute_to_goal(
    db: Session, goal_id: int, amount: float
) -> Optional[models.SavingsGoal]:
    goal = get_savings_goal_by_id(db, goal_id)
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

