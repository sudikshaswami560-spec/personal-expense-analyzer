import io
import csv
import os
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from .database import engine, Base, get_db, SessionLocal
from . import models, schemas, crud
from .seed import seed_sample_expenses_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed initial sample data if empty
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_sample_expenses_if_empty(db)
    yield
    # Shutdown logic (if any)


app = FastAPI(
    title="Personal Expense Analyzer API",
    description="A clean REST API for recording and analyzing personal expenses.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup: supports local development, production Vercel domains, and configurable origins via environment variables
cors_env = os.getenv("CORS_ORIGINS", "")
if cors_env:
    allowed_origins = [orig.strip() for orig in cors_env.split(",") if orig.strip()]
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    clean_frontend_url = frontend_url.rstrip("/")
    if clean_frontend_url not in allowed_origins:
        allowed_origins.append(clean_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Automatically permits all Vercel production & preview domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
def read_root():
    return {
        "name": "Personal Expense Analyzer API",
        "status": "online",
        "documentation": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["General"])
def health_check():
    return {"status": "healthy"}


@app.get("/api/meta", tags=["Metadata"])
def get_metadata(db: Session = Depends(get_db)):
    """Returns available categories, payment methods, and distinct months with records."""
    recorded_months = crud.get_available_months(db)
    return {
        "categories": schemas.CATEGORIES,
        "payment_methods": schemas.PAYMENT_METHODS,
        "recorded_months": recorded_months,
        "income_sources": schemas.INCOME_SOURCES,
    }


@app.get("/api/expenses", response_model=List[schemas.ExpenseResponse], tags=["Expenses"])
def list_expenses(
    month: Optional[str] = Query(None, description="Filter by YYYY-MM"),
    start_date: Optional[str] = Query(None, description="Filter start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Filter end date YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="Filter by category"),
    payment_method: Optional[str] = Query(None, description="Filter by payment method"),
    search: Optional[str] = Query(None, description="Search description or category"),
    sort_by: str = Query("date", description="Sort by field: date or amount"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
):
    """Retrieve expenses with optional filtering by month, date range, category, payment method, or search query."""
    return crud.get_expenses(
        db=db,
        month=month,
        start_date=start_date,
        end_date=end_date,
        category=category,
        payment_method=payment_method,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@app.post(
    "/api/expenses",
    response_model=schemas.ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Expenses"],
)
def add_expense(
    expense_data: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
):
    """Add a new expense."""
    return crud.create_expense(db=db, expense_data=expense_data)


@app.post(
    "/api/expenses/bulk-delete",
    response_model=schemas.BulkDeleteResponse,
    status_code=status.HTTP_200_OK,
    tags=["Expenses"],
)
def bulk_delete_expenses(
    payload: schemas.BulkDeleteRequest,
    db: Session = Depends(get_db),
):
    """Delete multiple selected expenses by ID."""
    deleted_count = crud.bulk_delete_expenses(db=db, ids=payload.ids)
    return schemas.BulkDeleteResponse(
        deleted_count=deleted_count,
        ids=payload.ids,
        message=f"Successfully deleted {deleted_count} expenses.",
    )


@app.get("/api/expenses/{expense_id}", response_model=schemas.ExpenseResponse, tags=["Expenses"])
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
):
    """Get single expense by its ID."""
    expense = crud.get_expense_by_id(db=db, expense_id=expense_id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found",
        )
    return expense


@app.put("/api/expenses/{expense_id}", response_model=schemas.ExpenseResponse, tags=["Expenses"])
def update_expense(
    expense_id: int,
    expense_data: schemas.ExpenseUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing expense."""
    updated = crud.update_expense(db=db, expense_id=expense_id, expense_data=expense_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found",
        )
    return updated


@app.delete("/api/expenses/{expense_id}", status_code=status.HTTP_200_OK, tags=["Expenses"])
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
):
    """Delete an expense by ID."""
    deleted = crud.delete_expense(db=db, expense_id=expense_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found",
        )
    return {"message": f"Expense {expense_id} deleted successfully", "id": expense_id}


@app.get(
    "/api/analytics/summary",
    response_model=schemas.AnalyticsSummaryResponse,
    tags=["Analytics"],
)
def get_summary(
    month: Optional[str] = Query(None, description="Filter summary by YYYY-MM"),
    start_date: Optional[str] = Query(None, description="Filter start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Filter end date YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="Filter summary by category"),
    payment_method: Optional[str] = Query(None, description="Filter summary by payment method"),
    db: Session = Depends(get_db),
):
    """Get aggregate statistics: total spending, count, average, category breakdown, monthly trends."""
    return crud.get_analytics_summary(
        db=db,
        month=month,
        start_date=start_date,
        end_date=end_date,
        category=category,
        payment_method=payment_method,
    )


@app.get(
    "/api/analytics/comparison",
    response_model=schemas.PeriodComparisonResponse,
    tags=["Analytics"],
)
def compare_periods(
    current_start: str = Query(..., description="Current period start date YYYY-MM-DD"),
    current_end: str = Query(..., description="Current period end date YYYY-MM-DD"),
    prev_start: str = Query(..., description="Previous period start date YYYY-MM-DD"),
    prev_end: str = Query(..., description="Previous period end date YYYY-MM-DD"),
    current_label: str = Query("Current Period", description="Display label for current period"),
    prev_label: str = Query("Previous Period", description="Display label for previous period"),
    db: Session = Depends(get_db),
):
    """Compares spending between two date periods, calculating deltas in INR and percentages."""
    return crud.get_period_comparison(
        db=db,
        current_start=current_start,
        current_end=current_end,
        prev_start=prev_start,
        prev_end=prev_end,
        current_label=current_label,
        prev_label=prev_label,
    )


@app.get("/api/export/expenses", tags=["Export"])
def export_expenses(
    format: str = Query("csv", description="Format: csv or excel"),
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export expenses as a downloadable CSV or Excel spreadsheet."""
    expenses = crud.get_expenses(
        db=db,
        month=month,
        start_date=start_date,
        end_date=end_date,
        category=category,
        payment_method=payment_method,
        search=search,
        sort_by="date",
        sort_order="asc",
    )

    if format.lower() == "excel":
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Expenses"
        headers = ["Transaction ID", "Date", "Description", "Category", "Payment Method", "Amount (INR)"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")

        for exp in expenses:
            ws.append([exp.id, exp.date, exp.description, exp.category, exp.payment_method, exp.amount])

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        filename = f"expenses_{month or 'all'}.xlsx"
        return Response(
            content=out.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    else:
        output = io.StringIO()
        output.write("\ufeff")  # UTF-8 BOM for clean Excel viewing
        writer = csv.writer(output)
        writer.writerow(["Transaction ID", "Date", "Description", "Category", "Payment Method", "Amount (INR)"])
        for exp in expenses:
            writer.writerow([exp.id, exp.date, exp.description, exp.category, exp.payment_method, f"{exp.amount:.2f}"])
        filename = f"expenses_{month or 'all'}.csv"
        return Response(
            content=output.getvalue().encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )


@app.get("/api/export/summary", tags=["Export"])
def export_summary(
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("csv"),
    db: Session = Depends(get_db),
):
    """Export spending overview & category breakdown as CSV or Excel."""
    summary = crud.get_analytics_summary(
        db=db, month=month, start_date=start_date, end_date=end_date
    )

    if format.lower() == "excel":
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Financial Summary"
        ws.append(["Metric", "Value"])
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
        ws.append(["Total Spending (INR)", summary.total_spending])
        ws.append(["Total Expenses Count", summary.total_expenses_count])
        ws.append(["Average Expense (INR)", summary.average_expense])
        ws.append(["Highest Expense (INR)", summary.highest_expense])
        ws.append([])
        ws.append(["Category Breakdown"])
        ws.append(["Category", "Total Amount (INR)", "Share (%)", "Transaction Count"])
        header_row = ws.max_row
        for cell in ws[header_row]:
            cell.font = Font(bold=True)
        for cat in summary.categories:
            ws.append([cat.category, cat.total_amount, f"{cat.percentage}%", cat.count])
        ws.append([])
        ws.append(["Payment Method Breakdown"])
        ws.append(["Payment Method", "Total Amount (INR)", "Share (%)", "Transaction Count"])
        header_row = ws.max_row
        for cell in ws[header_row]:
            cell.font = Font(bold=True)
        for pm in summary.payment_methods:
            ws.append([pm.payment_method, pm.total_amount, f"{pm.percentage}%", pm.count])

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 16)

        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        period_slug = month or (f"{start_date}_to_{end_date}" if start_date and end_date else start_date or "all")
        filename = f"summary_{period_slug}.xlsx"
        return Response(
            content=out.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    else:
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)
        writer.writerow(["Expense Analyzer Summary Report"])
        period_str = month or (f"{start_date} to {end_date}" if start_date and end_date else "All Time")
        writer.writerow(["Period", period_str])
        writer.writerow([])
        writer.writerow(["Overview Metrics"])
        writer.writerow(["Total Spending (INR)", f"{summary.total_spending:.2f}"])
        writer.writerow(["Transaction Count", summary.total_expenses_count])
        writer.writerow(["Average Expense (INR)", f"{summary.average_expense:.2f}"])
        writer.writerow(["Highest Expense (INR)", f"{summary.highest_expense:.2f}"])
        writer.writerow([])
        writer.writerow(["Category Breakdown"])
        writer.writerow(["Category", "Total Amount (INR)", "Share (%)", "Count"])
        for cat in summary.categories:
            writer.writerow([cat.category, f"{cat.total_amount:.2f}", f"{cat.percentage}%", cat.count])
        writer.writerow([])
        writer.writerow(["Payment Method Breakdown"])
        writer.writerow(["Payment Method", "Total Amount (INR)", "Share (%)", "Count"])
        for pm in summary.payment_methods:
            writer.writerow([pm.payment_method, f"{pm.total_amount:.2f}", f"{pm.percentage}%", pm.count])

        period_slug = month or (f"{start_date}_to_{end_date}" if start_date and end_date else start_date or "all")
        filename = f"summary_{period_slug}.csv"
        return Response(
            content=output.getvalue().encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )


@app.get(
    "/api/monthly-summaries",
    response_model=List[schemas.MonthlySummaryResponse],
    tags=["Monthly Summaries"],
)
def list_monthly_summaries(db: Session = Depends(get_db)):
    """Retrieve all monthly expense summaries."""
    summaries = crud.get_monthly_summaries(db)
    result = []
    for s in summaries:
        # compute itemized total for context
        itemized_expenses = crud.get_expenses(db, month=s.month)
        itemized_total = round(sum(e.amount for e in itemized_expenses), 2)
        resp = schemas.MonthlySummaryResponse(
            id=s.id,
            month=s.month,
            total_amount=round(s.total_amount, 2),
            note=s.note,
            created_at=s.created_at,
            updated_at=s.updated_at,
            itemized_total=itemized_total,
            itemized_count=len(itemized_expenses),
        )
        result.append(resp)
    return result


@app.get(
    "/api/monthly-summaries/{month}",
    response_model=schemas.MonthlySummaryResponse,
    tags=["Monthly Summaries"],
)
def get_monthly_summary(month: str, db: Session = Depends(get_db)):
    """Get the monthly summary for a specific month (YYYY-MM)."""
    s = crud.get_monthly_summary_by_month(db, month)
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No monthly summary found for {month}",
        )
    itemized_expenses = crud.get_expenses(db, month=s.month)
    itemized_total = round(sum(e.amount for e in itemized_expenses), 2)
    return schemas.MonthlySummaryResponse(
        id=s.id,
        month=s.month,
        total_amount=round(s.total_amount, 2),
        note=s.note,
        created_at=s.created_at,
        updated_at=s.updated_at,
        itemized_total=itemized_total,
        itemized_count=len(itemized_expenses),
    )


@app.post(
    "/api/monthly-summaries",
    response_model=schemas.MonthlySummaryResponse,
    status_code=status.HTTP_200_OK,
    tags=["Monthly Summaries"],
)
def set_monthly_summary(
    summary_data: schemas.MonthlySummaryCreate,
    db: Session = Depends(get_db),
):
    """
    Create or update a monthly summary.
    Treats this amount as the official overall total for the month, preventing double-counting
    while preserving all existing individual expense records.
    """
    s = crud.upsert_monthly_summary(db, summary_data)
    itemized_expenses = crud.get_expenses(db, month=s.month)
    itemized_total = round(sum(e.amount for e in itemized_expenses), 2)
    return schemas.MonthlySummaryResponse(
        id=s.id,
        month=s.month,
        total_amount=round(s.total_amount, 2),
        note=s.note,
        created_at=s.created_at,
        updated_at=s.updated_at,
        itemized_total=itemized_total,
        itemized_count=len(itemized_expenses),
    )


@app.delete(
    "/api/monthly-summaries/{month}",
    status_code=status.HTTP_200_OK,
    tags=["Monthly Summaries"],
)
def remove_monthly_summary(month: str, db: Session = Depends(get_db)):
    """Delete a monthly summary, reverting the month's total to its itemized expense sum."""
    deleted = crud.delete_monthly_summary(db, month)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No monthly summary found for {month}",
        )
    return {"message": f"Monthly summary for {month} removed successfully", "month": month}


# ==========================================
# STAGE 2: BUDGETS ENDPOINTS
# ==========================================

@app.get(
    "/api/budgets",
    response_model=List[schemas.BudgetResponse],
    tags=["Budgets"],
)
def list_budgets(
    month: Optional[str] = Query(None, description="Optional YYYY-MM to filter"),
    db: Session = Depends(get_db),
):
    """List budgets and their spending progress."""
    if month and month.lower() != "all":
        b = crud.get_budget_by_month(db, month)
        return [crud.build_budget_response(db, b)] if b else []
    budgets = crud.get_budgets(db)
    return [crud.build_budget_response(db, b) for b in budgets]


@app.get(
    "/api/budgets/{month}",
    response_model=schemas.BudgetResponse,
    tags=["Budgets"],
)
def get_budget_for_month(month: str, db: Session = Depends(get_db)):
    """Get budget and spending calculation for a specific month."""
    b = crud.get_budget_by_month(db, month)
    if not b:
        raise HTTPException(status_code=404, detail=f"No budget found for month {month}")
    return crud.build_budget_response(db, b)


@app.post(
    "/api/budgets",
    response_model=schemas.BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Budgets"],
)
def set_budget(
    budget_data: schemas.BudgetCreate,
    db: Session = Depends(get_db),
):
    """Create or update a monthly budget with overall and category limits."""
    b = crud.upsert_budget(db, budget_data)
    return crud.build_budget_response(db, b)


@app.delete(
    "/api/budgets/{month}",
    tags=["Budgets"],
)
def delete_budget(month: str, db: Session = Depends(get_db)):
    """Delete a budget for a given month."""
    deleted = crud.delete_budget(db, month)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No budget found for {month}")
    return {"message": f"Budget for {month} deleted successfully", "month": month}


# ==========================================
# STAGE 2: INCOME ENDPOINTS
# ==========================================

@app.get(
    "/api/incomes",
    response_model=List[schemas.IncomeResponse],
    tags=["Income"],
)
def list_incomes(
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve recorded income entries."""
    return crud.get_incomes(
        db, month=month, start_date=start_date, end_date=end_date, source=source
    )


@app.post(
    "/api/incomes",
    response_model=schemas.IncomeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Income"],
)
def add_income(income_in: schemas.IncomeCreate, db: Session = Depends(get_db)):
    """Record a new income entry."""
    return crud.create_income(db, income_in)


@app.put(
    "/api/incomes/{income_id}",
    response_model=schemas.IncomeResponse,
    tags=["Income"],
)
def modify_income(
    income_id: int,
    income_in: schemas.IncomeUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing income record."""
    updated = crud.update_income(db, income_id, income_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Income record not found")
    return updated


@app.delete(
    "/api/incomes/{income_id}",
    tags=["Income"],
)
def remove_income(income_id: int, db: Session = Depends(get_db)):
    """Delete an income entry."""
    deleted = crud.delete_income(db, income_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Income record not found")
    return {"message": "Income deleted successfully", "id": income_id}


@app.get(
    "/api/analytics/cashflow",
    response_model=schemas.CashFlowSummaryResponse,
    tags=["Income"],
)
def get_cash_flow(
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Compute cash flow: Total Income, Total Expenses, Net Savings, and Savings Rate."""
    return crud.get_cash_flow_summary(
        db, month=month, start_date=start_date, end_date=end_date
    )


# ==========================================
# STAGE 2: RECURRING EXPENSES ENDPOINTS
# ==========================================

@app.get(
    "/api/recurring-expenses",
    response_model=List[schemas.RecurringExpenseResponse],
    tags=["Recurring Expenses"],
)
def list_recurring_expenses(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """List recurring subscriptions, rent, and utility commitments."""
    return crud.get_recurring_expenses(db, status=status_filter)


@app.post(
    "/api/recurring-expenses",
    response_model=schemas.RecurringExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Recurring Expenses"],
)
def add_recurring_expense(
    rec_in: schemas.RecurringExpenseCreate,
    db: Session = Depends(get_db),
):
    """Create a new recurring expense schedule."""
    return crud.create_recurring_expense(db, rec_in)


@app.put(
    "/api/recurring-expenses/{recurring_id}",
    response_model=schemas.RecurringExpenseResponse,
    tags=["Recurring Expenses"],
)
def modify_recurring_expense(
    recurring_id: int,
    rec_in: schemas.RecurringExpenseUpdate,
    db: Session = Depends(get_db),
):
    """Update a recurring expense schedule."""
    updated = crud.update_recurring_expense(db, recurring_id, rec_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return updated


@app.delete(
    "/api/recurring-expenses/{recurring_id}",
    tags=["Recurring Expenses"],
)
def remove_recurring_expense(recurring_id: int, db: Session = Depends(get_db)):
    """Delete a recurring expense schedule."""
    deleted = crud.delete_recurring_expense(db, recurring_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return {"message": "Recurring expense deleted successfully", "id": recurring_id}


@app.post(
    "/api/recurring-expenses/{recurring_id}/toggle-status",
    response_model=schemas.RecurringExpenseResponse,
    tags=["Recurring Expenses"],
)
def toggle_recurring_expense_status(
    recurring_id: int,
    new_status: str = Query(..., description="active, paused, or stopped"),
    db: Session = Depends(get_db),
):
    """Change recurring expense status (e.g. pause or stop)."""
    if new_status not in schemas.RECURRING_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(schemas.RECURRING_STATUSES)}",
        )
    updated = crud.toggle_recurring_status(db, recurring_id, new_status)
    if not updated:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return updated


@app.post(
    "/api/recurring-expenses/{recurring_id}/record-due",
    tags=["Recurring Expenses"],
)
def record_due_recurring_expense(recurring_id: int, db: Session = Depends(get_db)):
    """
    1-click action to record a due recurring expense into the Expense table
    and advance the next_due_date automatically.
    """
    expense, recurring = crud.record_due_expense(db, recurring_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return {
        "message": f"Recorded expense '{expense.description}' for INR {expense.amount:.2f}",
        "expense_id": expense.id,
        "next_due_date": recurring.next_due_date,
    }


# ==========================================
# STAGE 2: SAVINGS GOALS ENDPOINTS
# ==========================================

@app.get(
    "/api/savings-goals",
    response_model=List[schemas.SavingsGoalResponse],
    tags=["Savings Goals"],
)
def list_savings_goals(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """List savings goals with progress percentages and remaining targets."""
    goals = crud.get_savings_goals(db, status=status_filter)
    return [crud.build_savings_goal_response(g) for g in goals]


@app.post(
    "/api/savings-goals",
    response_model=schemas.SavingsGoalResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Savings Goals"],
)
def add_savings_goal(
    goal_in: schemas.SavingsGoalCreate,
    db: Session = Depends(get_db),
):
    """Create a new savings goal target."""
    goal = crud.create_savings_goal(db, goal_in)
    return crud.build_savings_goal_response(goal)


@app.put(
    "/api/savings-goals/{goal_id}",
    response_model=schemas.SavingsGoalResponse,
    tags=["Savings Goals"],
)
def modify_savings_goal(
    goal_id: int,
    goal_in: schemas.SavingsGoalUpdate,
    db: Session = Depends(get_db),
):
    """Update a savings goal."""
    goal = crud.update_savings_goal(db, goal_id, goal_in)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return crud.build_savings_goal_response(goal)


@app.delete(
    "/api/savings-goals/{goal_id}",
    tags=["Savings Goals"],
)
def remove_savings_goal(goal_id: int, db: Session = Depends(get_db)):
    """Delete a savings goal."""
    deleted = crud.delete_savings_goal(db, goal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return {"message": "Savings goal deleted successfully", "id": goal_id}


@app.post(
    "/api/savings-goals/{goal_id}/contribute",
    response_model=schemas.SavingsGoalResponse,
    tags=["Savings Goals"],
)
def add_contribution(
    goal_id: int,
    contrib: schemas.GoalContributionRequest,
    db: Session = Depends(get_db),
):
    """Add a contribution in INR to a savings target."""
    goal = crud.contribute_to_goal(db, goal_id, contrib.amount)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return crud.build_savings_goal_response(goal)

