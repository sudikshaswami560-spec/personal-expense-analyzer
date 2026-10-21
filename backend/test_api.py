from app.database import engine, Base, SessionLocal
from app.seed import seed_sample_expenses_if_empty
from app import crud, schemas

def run_tests():
    print("1. Initializing database and testing seeding...")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_sample_expenses_if_empty(db)
        expenses = crud.get_expenses(db)
        print(f"   Seeded expenses count: {len(expenses)}")
        assert len(expenses) > 0, "Expected seeded expenses"

        print("2. Testing create expense...")
        payload = schemas.ExpenseCreate(
            amount=34.99,
            description="Wireless Mouse",
            category="Shopping",
            date="2026-09-25",
            payment_method="Credit Card",
        )
        created = crud.create_expense(db, payload)
        expense_id = created.id
        print(f"   Created expense ID {expense_id}: {created.description} (${created.amount})")
        assert created.amount == 34.99

        print("3. Testing get expense by id...")
        fetched = crud.get_expense_by_id(db, expense_id)
        assert fetched is not None
        assert fetched.id == expense_id

        print("4. Testing update expense...")
        update_data = schemas.ExpenseUpdate(amount=39.99, description="Wireless Mouse (Silent)")
        updated = crud.update_expense(db, expense_id, update_data)
        assert updated.amount == 39.99
        assert updated.description == "Wireless Mouse (Silent)"
        print("   Updated successfully!")

        print("5. Testing analytics calculation...")
        summary = crud.get_analytics_summary(db)
        assert summary.total_spending > 0
        assert summary.total_expenses_count > 0
        assert summary.average_expense > 0
        assert len(summary.categories) > 0
        assert len(summary.monthly_trends) > 0
        print(f"   Summary total: ${summary.total_spending:.2f}, Average: ${summary.average_expense:.2f}, Categories: {len(summary.categories)}")

        print("6. Testing delete expense...")
        deleted = crud.delete_expense(db, expense_id)
        assert deleted is True
        assert crud.get_expense_by_id(db, expense_id) is None
        print("   Deleted successfully!")

        print("7. Testing Monthly Expense Summary feature...")
        # Get baseline for month 2026-09
        month_summary_baseline = crud.get_analytics_summary(db, month="2026-09")
        baseline_spending = month_summary_baseline.total_spending
        baseline_expenses = crud.get_expenses(db, month="2026-09")
        baseline_count = len(baseline_expenses)
        print(f"   Baseline 2026-09 itemized spending: ${baseline_spending:.2f} ({baseline_count} records)")

        # Create a monthly summary overriding 2026-09 with $500.00
        summary_payload = schemas.MonthlySummaryCreate(
            month="2026-09",
            total_amount=500.00,
            note="Lump-sum bank statement estimate",
        )
        saved_summary = crud.upsert_monthly_summary(db, summary_payload)
        assert saved_summary.total_amount == 500.00
        print(f"   Saved monthly summary for 2026-09: ${saved_summary.total_amount:.2f}")

        # Check analytics for 2026-09
        analytics_with_summary = crud.get_analytics_summary(db, month="2026-09")
        assert analytics_with_summary.has_monthly_summary is True
        assert analytics_with_summary.total_spending == 500.00, f"Expected 500.00, got {analytics_with_summary.total_spending}"
        print(f"   Analytics 2026-09 with summary total: ${analytics_with_summary.total_spending:.2f} (Double counting prevented!)")

        # Verify individual expenses are preserved
        expenses_after_summary = crud.get_expenses(db, month="2026-09")
        assert len(expenses_after_summary) == baseline_count, "Individual expenses were altered!"
        print(f"   Individual expenses preserved count: {len(expenses_after_summary)}")

        # Check monthly trend for 2026-09
        trends = crud.get_monthly_trends(db)
        sep_trend = next((t for t in trends if t.month == "2026-09"), None)
        assert sep_trend is not None
        assert sep_trend.is_summary is True
        assert sep_trend.total_amount == 500.00
        assert sep_trend.itemized_amount == baseline_spending
        print("   Monthly trend shows summary total with is_summary=True OK!")

        # Clean up monthly summary
        del_success = crud.delete_monthly_summary(db, "2026-09")
        assert del_success is True
        reverted_analytics = crud.get_analytics_summary(db, month="2026-09")
        assert reverted_analytics.has_monthly_summary is False
        assert reverted_analytics.total_spending == baseline_spending
        print("   Reverted to itemized sum upon deleting monthly summary OK!")

        print("8. Testing Date Range Filtering & Bulk Deletion...")
        # Create 2 test expenses
        exp1 = crud.create_expense(db, schemas.ExpenseCreate(
            amount=100.0, description="Test Expense 1", category="Shopping", date="2026-10-01", payment_method="UPI"
        ))
        exp2 = crud.create_expense(db, schemas.ExpenseCreate(
            amount=200.0, description="Test Expense 2", category="Groceries", date="2026-10-05", payment_method="Cash"
        ))

        # Test date range
        range_expenses = crud.get_expenses(db, start_date="2026-10-01", end_date="2026-10-05")
        range_ids = [e.id for e in range_expenses]
        assert exp1.id in range_ids and exp2.id in range_ids
        print(f"   Date range filtering OK! Found {len(range_expenses)} expenses between 2026-10-01 and 2026-10-05")

        # Test period comparison
        comparison = crud.get_period_comparison(
            db=db,
            current_start="2026-10-01",
            current_end="2026-10-31",
            prev_start="2026-09-01",
            prev_end="2026-09-30",
            current_label="October 2026",
            prev_label="September 2026",
        )
        assert comparison.current_period_spending > 0
        assert len(comparison.category_deltas) > 0
        print(f"   Period comparison OK! Oct vs Sep delta: {comparison.difference:+.2f} ({comparison.percentage_change:+.1f}%)")

        id1 = exp1.id
        id2 = exp2.id
        # Test bulk deletion
        deleted_count = crud.bulk_delete_expenses(db, [id1, id2])
        assert deleted_count == 2
        assert crud.get_expense_by_id(db, id1) is None
        assert crud.get_expense_by_id(db, id2) is None
        print(f"   Bulk deletion OK! Deleted {deleted_count} expenses.")

        print("9. Testing Stage 2: Budgets with Real-time Alerts...")
        budget_in = schemas.BudgetCreate(
            month="2026-10",
            overall_limit=5000.0,
            category_limits={"Shopping": 2000.0, "Food & Dining": 1000.0},
        )
        saved_budget = crud.upsert_budget(db, budget_in)
        assert saved_budget.overall_limit == 5000.0
        budget_resp = crud.build_budget_response(db, saved_budget)
        assert budget_resp.overall_remaining >= 0
        assert len(budget_resp.category_limits) == 2
        print(f"   Budget OK! Limit: INR {budget_resp.overall_limit}, Spent: INR {budget_resp.overall_spent}, Status: {budget_resp.overall_status}")
        crud.delete_budget(db, "2026-10")

        print("10. Testing Stage 2: Income Tracking & Net Balance Cash Flow...")
        inc1 = crud.create_income(db, schemas.IncomeCreate(
            amount=50000.0, source="Salary", date="2026-10-01", description="Monthly Tech Salary"
        ))
        inc2 = crud.create_income(db, schemas.IncomeCreate(
            amount=5000.0, source="Freelance", date="2026-10-15", description="Web Design Client"
        ))
        cashflow = crud.get_cash_flow_summary(db, month="2026-10")
        assert cashflow.total_income == 55000.0
        assert cashflow.net_balance > 0
        assert len(cashflow.income_sources) == 2
        print(f"   Cashflow OK! Total Income: INR {cashflow.total_income}, Net Balance: INR {cashflow.net_balance}, Savings Rate: {cashflow.savings_rate}%")
        crud.delete_income(db, inc1.id)
        crud.delete_income(db, inc2.id)

        print("11. Testing Stage 2: Recurring Expenses & 1-Click Due Execution...")
        rec = crud.create_recurring_expense(db, schemas.RecurringExpenseCreate(
            amount=499.0,
            description="Netflix Subscription",
            category="Entertainment",
            payment_method="Credit Card",
            frequency="monthly",
            start_date="2026-10-01",
            next_due_date="2026-10-25",
            status="active",
        ))
        assert rec.id is not None
        # Test 1-click execution
        created_exp, updated_rec = crud.record_due_expense(db, rec.id)
        assert created_exp is not None
        assert created_exp.amount == 499.0
        assert updated_rec.next_due_date > "2026-10-25"
        print(f"   Recurring OK! Generated expense {created_exp.id}, next due advanced to {updated_rec.next_due_date}")
        crud.delete_expense(db, created_exp.id)
        crud.delete_recurring_expense(db, rec.id)

        print("12. Testing Stage 2: Savings Goals & Progress Contributions...")
        goal = crud.create_savings_goal(db, schemas.SavingsGoalCreate(
            title="Emergency Fund",
            target_amount=100000.0,
            current_amount=25000.0,
            target_date="2027-03-31",
            category="Savings",
        ))
        goal_resp = crud.build_savings_goal_response(goal)
        assert goal_resp.percentage_complete == 25.0
        assert goal_resp.remaining_amount == 75000.0
        # Add contribution
        updated_goal = crud.contribute_to_goal(db, goal.id, 15000.0)
        assert updated_goal.current_amount == 40000.0
        goal_resp2 = crud.build_savings_goal_response(updated_goal)
        assert goal_resp2.percentage_complete == 40.0
        print(f"   Savings Goal OK! Target: INR {goal_resp2.target_amount}, Current: INR {goal_resp2.current_amount} ({goal_resp2.percentage_complete}%)")
        crud.delete_savings_goal(db, goal.id)

    print("\nALL BACKEND UNIT TESTS (STAGE 1 & STAGE 2) PASSED SUCCESSFULLY! :)")

if __name__ == "__main__":
    run_tests()

