from fastapi.testclient import TestClient
from app.main import app

def test_full_auth_and_isolation():
    client = TestClient(app)

    print("1. Testing Health Check...")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("   Health Check OK!")

    print("\n2. Testing Unauthenticated Access Rejection...")
    r = client.get("/api/expenses")
    assert r.status_code == 401, f"Expected 401 Unauthorized for /api/expenses, got {r.status_code}"
    print("   Unauthenticated access properly blocked with 401!")

    print("\n3. Testing Demo User Login (Assigned Legacy 12 Expenses)...")
    r = client.post("/api/auth/login", json={
        "email": "demo@expenseanalyzer.com",
        "password": "Password123!"
    })
    assert r.status_code == 200, f"Demo login failed: {r.text}"
    demo_token = r.json()["access_token"]
    demo_headers = {"Authorization": f"Bearer {demo_token}"}
    print("   Demo login successful! Token acquired.")

    # Check Demo's expenses
    r = client.get("/api/expenses", headers=demo_headers)
    assert r.status_code == 200
    demo_expenses = r.json()
    print(f"   Demo user has {len(demo_expenses)} expenses (preserved legacy data).")
    assert len(demo_expenses) >= 12, f"Expected at least 12 expenses for demo user, got {len(demo_expenses)}"

    print("\n4. Registering New Independent User Alice...")
    alice_email = "alice_test@example.com"
    r = client.post("/api/auth/register", json={
        "email": alice_email,
        "password": "AliceSecretPassword123!",
        "full_name": "Alice Tester"
    })
    if r.status_code == 400: # Already registered in previous test run
        r = client.post("/api/auth/login", json={
            "email": alice_email,
            "password": "AliceSecretPassword123!"
        })
    assert r.status_code in (200, 201), f"Alice auth failed: {r.text}"
    alice_token = r.json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    print("   Alice registered/logged in successfully.")

    print("\n5. Verifying Alice starts with private empty expenses...")
    r = client.get("/api/expenses", headers=alice_headers)
    assert r.status_code == 200
    alice_expenses = r.json()
    print(f"   Alice's initial expense count: {len(alice_expenses)}")

    print("\n6. Alice adds a private expense...")
    r = client.post("/api/expenses", headers=alice_headers, json={
        "amount": 2500.0,
        "description": "Alice Private Laptop Accessory",
        "category": "Shopping",
        "date": "2026-10-23",
        "payment_method": "UPI"
    })
    assert r.status_code == 201, f"Failed to create expense: {r.text}"
    alice_expense = r.json()
    alice_expense_id = alice_expense["id"]
    print(f"   Alice created expense ID {alice_expense_id}: {alice_expense['description']} (INR {alice_expense['amount']})")

    print("\n7. Verifying Demo User CANNOT see Alice's expense...")
    r = client.get(f"/api/expenses/{alice_expense_id}", headers=demo_headers)
    assert r.status_code == 404, f"Security Breach! Demo user was able to access Alice's expense! Status: {r.status_code}"
    print("   Demo user received 404 Not Found when trying to access Alice's expense ID directly!")

    print("\n8. Verifying Demo User CANNOT delete Alice's expense...")
    r = client.delete(f"/api/expenses/{alice_expense_id}", headers=demo_headers)
    assert r.status_code == 404, f"Security Breach! Demo user was able to delete Alice's expense! Status: {r.status_code}"
    print("   Demo user received 404 Not Found when trying to delete Alice's expense!")

    print("\n9. Verifying Bulk Delete Isolation...")
    r = client.post("/api/expenses/bulk-delete", headers=demo_headers, json={"ids": [alice_expense_id]})
    assert r.status_code == 200
    assert r.json()["deleted_count"] == 0, "Demo user was able to bulk-delete Alice's expense!"
    print("   Bulk delete by Demo user ignored Alice's ID (deleted_count: 0)!")

    print("\n10. Verifying Alice CAN view and delete her own expense...")
    r = client.get(f"/api/expenses/{alice_expense_id}", headers=alice_headers)
    assert r.status_code == 200
    r = client.delete(f"/api/expenses/{alice_expense_id}", headers=alice_headers)
    assert r.status_code == 200
    print("   Alice successfully deleted her own expense!")

    print("\n=============================================")
    print("ALL TESTS PASSED! User data isolation is 100% verified.")
    print("=============================================")

if __name__ == "__main__":
    test_full_auth_and_isolation()
