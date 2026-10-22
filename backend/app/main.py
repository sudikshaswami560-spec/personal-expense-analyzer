import io
import csv
import os
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from .database import engine, Base, get_db, SessionLocal
from . import models, schemas, crud
from .migration import run_database_migrations
from .seed import seed_sample_expenses_if_empty
from .auth import (
    create_access_token,
    get_current_user,
    get_current_user_with_query_fallback,
    decode_token,
    security,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe schema migration executed FIRST before any query runs
    run_database_migrations()
    with SessionLocal() as db:
        seed_sample_expenses_if_empty(db)
    yield


app = FastAPI(
    title="Personal Expense Analyzer API",
    description="A secure multi-tenant REST API for recording and analyzing personal expenses.",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS setup
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
    allow_origin_regex=r"https://.*\.vercel\.app",  # Automatically permits all Vercel domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# GENERAL & HEALTH
# ==========================================

@app.get("/", tags=["General"])
def read_root():
    return {
        "name": "Personal Expense Analyzer API",
        "status": "online",
        "documentation": "/docs",
        "health": "/api/health",
        "version": "1.1.0 (Multi-User Secure)",
    }


@app.get("/api/health", tags=["General"])
def health_check():
    return {"status": "healthy"}


# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@app.post(
    "/api/auth/register",
    response_model=schemas.Token,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new private user account."""
    existing_user = crud.get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    user = crud.create_user(db, user_in)
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=schemas.UserResponse.model_validate(user),
    )


@app.post(
    "/api/auth/login",
    response_model=schemas.Token,
    tags=["Authentication"],
)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """Authenticate with email and password to receive a secure JWT token."""
    user = crud.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=schemas.UserResponse.model_validate(user),
    )


@app.get(
    "/api/auth/me",
    response_model=schemas.UserResponse,
    tags=["Authentication"],
)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Get profile of current authenticated user."""
    return current_user


# ==========================================
# METADATA ENDPOINT
# ==========================================

@app.get("/api/meta", tags=["Metadata"])
def get_metadata(
    db: Session = Depends(get_db),
    credentials=Depends(security),
):
    """Returns available categories, payment methods, and user's recorded months."""
    user_id = None
    if credentials and credentials.credentials:
        payload = decode_token(credentials.credentials)
        if payload and payload.get("sub"):
            try:
                user_id = int(payload["sub"])
            except ValueError:
                pass

    if user_id:
        recorded_months = crud.get_available_months(db, user_id=user_id)
    else:
        # Fallback to any recorded months if unauthenticated
        recorded_months = []

    return {
        "categories": schemas.CATEGORIES,
        "payment_methods": schemas.PAYMENT_METHODS,
        "recorded_months": recorded_months,
        "income_sources": schemas.INCOME_SOURCES,
    }


# ==========================================
# EXPENSES ENDPOINTS (SCOPED TO CURRENT USER)
# ==========================================

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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve expenses strictly belonging to the authenticated user."""
    return crud.get_expenses(
        db=db,
        user_id=current_user.id,
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new expense linked strictly to the authenticated user."""
    return crud.create_expense(db=db, expense_data=expense_data, user_id=current_user.id)


@app.post(
    "/api/expenses/bulk-delete",
    response_model=schemas.BulkDeleteResponse,
    status_code=status.HTTP_200_OK,
    tags=["Expenses"],
)
def bulk_delete_expenses(
    payload: schemas.BulkDeleteRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete multiple selected expenses belonging strictly to the authenticated user."""
    deleted_count = crud.bulk_delete_expenses(db=db, ids=payload.ids, user_id=current_user.id)
    return schemas.BulkDeleteResponse(
        deleted_count=deleted_count,
        ids=payload.ids,
        message=f"Successfully deleted {deleted_count} expenses.",
    )


@app.get("/api/expenses/{expense_id}", response_model=schemas.ExpenseResponse, tags=["Expenses"])
def get_expense(
    expense_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get single expense owned by the authenticated user."""
    expense = crud.get_expense_by_id(db=db, expense_id=expense_id, user_id=current_user.id)
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing expense owned by the authenticated user."""
    updated = crud.update_expense(
        db=db, expense_id=expense_id, expense_data=expense_data, user_id=current_user.id
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found",
        )
    return updated


@app.delete("/api/expenses/{expense_id}", status_code=status.HTTP_200_OK, tags=["Expenses"])
def delete_expense(
    expense_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an expense by ID owned by the authenticated user."""
    deleted = crud.delete_expense(db=db, expense_id=expense_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found",
        )
    return {"message": f"Expense {expense_id} deleted successfully", "id": expense_id}


# ==========================================
# ANALYTICS ENDPOINTS (SCOPED TO USER)
# ==========================================

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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get aggregate statistics scoped strictly to the authenticated user."""
    return crud.get_analytics_summary(
        db=db,
        user_id=current_user.id,
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compares spending between two date periods for the authenticated user."""
    return crud.get_period_comparison(
        db=db,
        user_id=current_user.id,
        current_start=current_start,
        current_end=current_end,
        prev_start=prev_start,
        prev_end=prev_end,
        current_label=current_label,
        prev_label=prev_label,
    )


# ==========================================
# EXPORT ENDPOINTS (SCOPED TO USER)
# ==========================================

@app.get("/api/export/expenses", tags=["Export"])
def export_expenses(
    format: str = Query("csv", description="Format: csv or excel"),
    month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: models.User = Depends(get_current_user_with_query_fallback),
    db: Session = Depends(get_db),
):
    """Export expenses as a downloadable CSV or Excel spreadsheet for the authenticated user."""
    expenses = crud.get_expenses(
        db=db,
        user_id=current_user.id,
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
        output.write("\ufeff")  # UTF-8 BOM
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
    current_user: models.User = Depends(get_current_user_with_query_fallback),
    db: Session = Depends(get_db),
):
    """Export spending overview & category breakdown as CSV or Excel for the authenticated user."""
    summary = crud.get_analytics_summary(
        db=db,
        user_id=current_user.id,
        month=month,
        start_date=start_date,
        end_date=end_date,
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


# ==========================================
# MONTHLY SUMMARIES ENDPOINTS (SCOPED TO USER)
# ==========================================

@app.get(
    "/api/monthly-summaries",
    response_model=List[schemas.MonthlySummaryResponse],
    tags=["Monthly Summaries"],
)
def list_monthly_summaries(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all monthly expense summaries for the current user."""
    summaries = crud.get_monthly_summaries(db, user_id=current_user.id)
    result = []
    for s in summaries:
        itemized_expenses = crud.get_expenses(db, user_id=current_user.id, month=s.month)
        itemized_total = round(sum(e.amount for e in itemized_expenses), 2)
        resp = schemas.MonthlySummaryResponse(
            id=s.id,
            user_id=current_user.id,
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
def get_monthly_summary(
    month: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the monthly summary for a specific month (YYYY-MM)."""
    s = crud.get_monthly_summary_by_month(db, month, user_id=current_user.id)
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No monthly summary found for {month}",
        )
    itemized_expenses = crud.get_expenses(db, user_id=current_user.id, month=s.month)
    itemized_total = round(sum(e.amount for e in itemized_expenses), 2)
    return schemas.MonthlySummaryResponse(
        id=s.id,
        user_id=current_user.id,
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a monthly summary for the authenticated user."""
    s = crud.upsert_monthly_summary(db, summary_data, user_id=current_user.id)
    itemized_expenses = crud.get_expenses(db, user_id=current_user.id, month=s.month)
    itemized_total = round(sum(e.amount for e in itemized_expenses), 2)
    return schemas.MonthlySummaryResponse(
        id=s.id,
        user_id=current_user.id,
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
def remove_monthly_summary(
    month: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a monthly summary for the authenticated user."""
    deleted = crud.delete_monthly_summary(db, month, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No monthly summary found for {month}",
        )
    return {"message": f"Monthly summary for {month} removed successfully", "month": month}


# ==========================================
# BUDGETS ENDPOINTS (SCOPED TO USER)
# ==========================================

@app.get(
    "/api/budgets",
    response_model=List[schemas.BudgetResponse],
    tags=["Budgets"],
)
def list_budgets(
    month: Optional[str] = Query(None, description="Optional YYYY-MM to filter"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List budgets and spending progress for current user."""
    if month and month.lower() != "all":
        b = crud.get_budget_by_month(db, month, user_id=current_user.id)
        return [crud.build_budget_response(db, b, user_id=current_user.id)] if b else []
    budgets = crud.get_budgets(db, user_id=current_user.id)
    return [crud.build_budget_response(db, b, user_id=current_user.id) for b in budgets]


@app.get(
    "/api/budgets/{month}",
    response_model=schemas.BudgetResponse,
    tags=["Budgets"],
)
def get_budget_for_month(
    month: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get budget for a specific month for current user."""
    b = crud.get_budget_by_month(db, month, user_id=current_user.id)
    if not b:
        raise HTTPException(status_code=404, detail=f"No budget found for month {month}")
    return crud.build_budget_response(db, b, user_id=current_user.id)


@app.post(
    "/api/budgets",
    response_model=schemas.BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Budgets"],
)
def set_budget(
    budget_data: schemas.BudgetCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a monthly budget for current user."""
    b = crud.upsert_budget(db, budget_data, user_id=current_user.id)
    return crud.build_budget_response(db, b, user_id=current_user.id)


@app.delete(
    "/api/budgets/{month}",
    tags=["Budgets"],
)
def delete_budget(
    month: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a budget for a given month for current user."""
    deleted = crud.delete_budget(db, month, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No budget found for {month}")
    return {"message": f"Budget for {month} deleted successfully", "month": month}


# ==========================================
# INCOME ENDPOINTS (SCOPED TO USER)
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve recorded income entries for current user."""
    return crud.get_incomes(
        db,
        user_id=current_user.id,
        month=month,
        start_date=start_date,
        end_date=end_date,
        source=source,
    )


@app.post(
    "/api/incomes",
    response_model=schemas.IncomeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Income"],
)
def add_income(
    income_in: schemas.IncomeCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a new income entry for current user."""
    return crud.create_income(db, income_in, user_id=current_user.id)


@app.put(
    "/api/incomes/{income_id}",
    response_model=schemas.IncomeResponse,
    tags=["Income"],
)
def modify_income(
    income_id: int,
    income_in: schemas.IncomeUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing income record owned by current user."""
    updated = crud.update_income(db, income_id, income_in, user_id=current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Income record not found")
    return updated


@app.delete(
    "/api/incomes/{income_id}",
    tags=["Income"],
)
def remove_income(
    income_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an income entry owned by current user."""
    deleted = crud.delete_income(db, income_id, user_id=current_user.id)
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute cash flow summary for current user."""
    return crud.get_cash_flow_summary(
        db,
        user_id=current_user.id,
        month=month,
        start_date=start_date,
        end_date=end_date,
    )


# ==========================================
# RECURRING EXPENSES ENDPOINTS (SCOPED TO USER)
# ==========================================

@app.get(
    "/api/recurring-expenses",
    response_model=List[schemas.RecurringExpenseResponse],
    tags=["Recurring Expenses"],
)
def list_recurring_expenses(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_recurring_expenses(db, user_id=current_user.id, status=status_filter)


@app.post(
    "/api/recurring-expenses",
    response_model=schemas.RecurringExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Recurring Expenses"],
)
def add_recurring_expense(
    rec_in: schemas.RecurringExpenseCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.create_recurring_expense(db, rec_in, user_id=current_user.id)


@app.put(
    "/api/recurring-expenses/{recurring_id}",
    response_model=schemas.RecurringExpenseResponse,
    tags=["Recurring Expenses"],
)
def modify_recurring_expense(
    recurring_id: int,
    rec_in: schemas.RecurringExpenseUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = crud.update_recurring_expense(db, recurring_id, rec_in, user_id=current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return updated


@app.delete(
    "/api/recurring-expenses/{recurring_id}",
    tags=["Recurring Expenses"],
)
def remove_recurring_expense(
    recurring_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = crud.delete_recurring_expense(db, recurring_id, user_id=current_user.id)
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if new_status not in schemas.RECURRING_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(schemas.RECURRING_STATUSES)}",
        )
    updated = crud.toggle_recurring_status(
        db, recurring_id, new_status, user_id=current_user.id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return updated


@app.post(
    "/api/recurring-expenses/{recurring_id}/record-due",
    tags=["Recurring Expenses"],
)
def record_due_recurring_expense(
    recurring_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense, recurring = crud.record_due_expense(
        db, recurring_id, user_id=current_user.id
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return {
        "message": f"Recorded expense '{expense.description}' for INR {expense.amount:.2f}",
        "expense_id": expense.id,
        "next_due_date": recurring.next_due_date,
    }


# ==========================================
# SAVINGS GOALS ENDPOINTS (SCOPED TO USER)
# ==========================================

@app.get(
    "/api/savings-goals",
    response_model=List[schemas.SavingsGoalResponse],
    tags=["Savings Goals"],
)
def list_savings_goals(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goals = crud.get_savings_goals(db, user_id=current_user.id, status=status_filter)
    return [crud.build_savings_goal_response(g) for g in goals]


@app.post(
    "/api/savings-goals",
    response_model=schemas.SavingsGoalResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Savings Goals"],
)
def add_savings_goal(
    goal_in: schemas.SavingsGoalCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = crud.create_savings_goal(db, goal_in, user_id=current_user.id)
    return crud.build_savings_goal_response(goal)


@app.put(
    "/api/savings-goals/{goal_id}",
    response_model=schemas.SavingsGoalResponse,
    tags=["Savings Goals"],
)
def modify_savings_goal(
    goal_id: int,
    goal_in: schemas.SavingsGoalUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = crud.update_savings_goal(db, goal_id, goal_in, user_id=current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return crud.build_savings_goal_response(goal)


@app.delete(
    "/api/savings-goals/{goal_id}",
    tags=["Savings Goals"],
)
def remove_savings_goal(
    goal_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = crud.delete_savings_goal(db, goal_id, user_id=current_user.id)
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = crud.contribute_to_goal(
        db, goal_id, contrib.amount, user_id=current_user.id
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return crud.build_savings_goal_response(goal)
