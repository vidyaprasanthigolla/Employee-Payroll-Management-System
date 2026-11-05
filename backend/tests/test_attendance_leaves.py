from datetime import date, time
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(username_or_email: str, password: str) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username_or_email, "password": password}
    )
    assert res.status_code == 200
    return res.json()["access_token"]


def test_employee_get_own_attendance():
    token = get_token("employee@payroll.com", "Employee@123")
    res = client.get("/api/v1/attendance/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    records = res.json()
    assert len(records) > 0
    assert records[0]["employee_code"] == "EMP1001"


def test_monthly_attendance_summary():
    emp_token = get_token("employee@payroll.com", "Employee@123")

    # Get John's employee record to get his ID
    me_res = client.get("/api/v1/employees/me", headers={"Authorization": f"Bearer {emp_token}"})
    john_id = me_res.json()["id"]

    res = client.get(
        f"/api/v1/attendance/summary/{john_id}?month=11&year=2026",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert res.status_code == 200
    summary = res.json()
    assert summary["month"] == 11
    assert summary["year"] == 2026
    assert summary["total_calendar_days"] == 30
    assert summary["present_days"] > 0
    assert summary["half_days"] == 1.0
    assert summary["absent_days"] == 1.0
    # Half days contribute 0.5 to unpaid LOP + 1 absent day = 1.5 unpaid days
    assert summary["unpaid_leave_days"] == 1.5


def test_mark_daily_attendance_and_auto_hours():
    hr_token = get_token("hr@payroll.com", "Hr@123")

    # Get Jane's employee ID
    emp_res = client.get("/api/v1/employees?search=Jane", headers={"Authorization": f"Bearer {hr_token}"})
    jane_id = emp_res.json()["items"][0]["id"]

    # Mark attendance with check_in 09:00 and check_out 18:00 (9 hours)
    att_payload = {
        "employee_id": jane_id,
        "date": "2026-11-25",
        "status": "PRESENT",
        "check_in": "09:00:00",
        "check_out": "18:00:00",
        "remarks": "On-time arrival"
    }

    res = client.post(
        "/api/v1/attendance",
        headers={"Authorization": f"Bearer {hr_token}"},
        json=att_payload
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "PRESENT"
    assert float(data["working_hours"]) == 9.0


def test_employee_get_leave_balances():
    emp_token = get_token("employee@payroll.com", "Employee@123")
    res = client.get("/api/v1/leaves/my-balances?year=2026", headers={"Authorization": f"Bearer {emp_token}"})
    assert res.status_code == 200
    balances = res.json()
    assert len(balances) >= 3

    bal_map = {b["leave_type"]: b for b in balances}
    assert float(bal_map["CASUAL"]["total_allocated"]) == 12.0
    assert float(bal_map["SICK"]["total_allocated"]) == 10.0
    assert float(bal_map["EARNED"]["total_allocated"]) == 15.0
    # Invariant: total_allocated == used + remaining
    for b in balances:
        assert float(b["total_allocated"]) == float(b["used"]) + float(b["remaining"])


def test_apply_leave_and_insufficient_balance_error():
    emp_token = get_token("employee@payroll.com", "Employee@123")

    # Apply for 50 days of sick leave (exceeds 10.0 available quota)
    payload = {
        "leave_type": "SICK",
        "start_date": "2026-12-01",
        "end_date": "2027-01-20",
        "reason": "Extended medical procedure"
    }

    res = client.post(
        "/api/v1/leaves/apply",
        headers={"Authorization": f"Bearer {emp_token}"},
        json=payload
    )
    assert res.status_code == 400
    assert "Insufficient" in res.json()["detail"]


def test_apply_and_approve_leave_deducts_quota():
    emp_token = get_token("employee@payroll.com", "Employee@123")
    hr_token = get_token("hr@payroll.com", "Hr@123")

    # Capture initial casual leave used count
    init_res = client.get("/api/v1/leaves/my-balances?year=2026", headers={"Authorization": f"Bearer {emp_token}"})
    initial_casual = next(b for b in init_res.json() if b["leave_type"] == "CASUAL")
    initial_used = float(initial_casual["used"])

    # 1. John Doe applies for 1 day of casual leave with dynamic unique date
    import time
    unique_day = 20 + int(time.time()) % 8  # 20..27
    date_str = f"2026-12-{unique_day:02d}"

    apply_payload = {
        "leave_type": "CASUAL",
        "start_date": date_str,
        "end_date": date_str,
        "reason": "Personal family event"
    }
    apply_res = client.post(
        "/api/v1/leaves/apply",
        headers={"Authorization": f"Bearer {emp_token}"},
        json=apply_payload
    )
    assert apply_res.status_code == 201
    leave_req = apply_res.json()
    assert leave_req["status"] == "PENDING"
    assert float(leave_req["days"]) == 1.0

    req_id = leave_req["id"]

    # 2. HR Manager reviews and approves the request
    review_res = client.patch(
        f"/api/v1/leaves/requests/{req_id}/review",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={"status": "APPROVED", "admin_remarks": "Approved by HR"}
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "APPROVED"

    # 3. Verify John's CASUAL leave used count increased by exactly 1.0
    bal_res = client.get("/api/v1/leaves/my-balances?year=2026", headers={"Authorization": f"Bearer {emp_token}"})
    balances = bal_res.json()
    casual_bal = next(b for b in balances if b["leave_type"] == "CASUAL")
    assert float(casual_bal["used"]) == initial_used + 1.0

    # 4. Verify that attendance on the date was automatically synced to ON_LEAVE
    att_res = client.get(
        f"/api/v1/attendance/me?start_date={date_str}&end_date={date_str}",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    records = att_res.json()
    assert len(records) == 1
    assert records[0]["status"] == "ON_LEAVE"


def test_rbac_employee_cannot_review_leave():
    emp_token = get_token("employee@payroll.com", "Employee@123")

    # Employee tries to review a leave request
    res = client.patch(
        "/api/v1/leaves/requests/1/review",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"status": "APPROVED"}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]
