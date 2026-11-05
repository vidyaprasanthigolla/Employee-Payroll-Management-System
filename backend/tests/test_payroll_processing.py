"""
Phase 8 – Payroll Processing Tests
===================================
Covers:
  • Monthly batch calculation (Gross / LOP / Net)
  • State machine: DRAFT → APPROVED → PAID
  • Duplicate-lock guard for finalized periods
  • Employee self-service payroll view
  • RBAC: employees cannot initiate or approve payroll

NOTE ON TEST ISOLATION
----------------------
All tests share a single SQLite database that persists between sessions.
The module-scoped ``reset_nov_payroll`` fixture wipes any existing
November 2026 payroll rows at the START of each test session so the
lifecycle tests always begin from a clean slate.
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.models.payroll import Payroll, PayrollDetail

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_token(username_or_email: str, password: str) -> str:
    """Authenticate and return a JWT access token."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username_or_email, "password": password}
    )
    assert res.status_code == 200, f"Login failed: {res.json()}"
    return res.json()["access_token"]


# ---------------------------------------------------------------------------
# Session-scoped fixture: wipe November 2026 payroll before tests run
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def reset_nov_payroll():
    """
    Delete all Payroll (and cascaded PayrollDetail) rows for month=11, year=2026
    so the lifecycle tests can always start from a DRAFT state.
    Runs once per test-session before any test in this module executes.
    """
    db = next(get_db())
    try:
        # Fetch matching payroll IDs
        payroll_ids = [
            row.id
            for row in db.query(Payroll).filter(
                Payroll.month == 11,
                Payroll.year == 2026
            ).all()
        ]
        # Delete detail lines first (FK constraint)
        if payroll_ids:
            db.query(PayrollDetail).filter(
                PayrollDetail.payroll_id.in_(payroll_ids)
            ).delete(synchronize_session=False)
        # Delete header rows
        db.query(Payroll).filter(
            Payroll.month == 11,
            Payroll.year == 2026
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

    yield  # run all tests in this module
    # (no teardown needed – next session will re-reset)


# ---------------------------------------------------------------------------
# Test 1: Batch calculation – DRAFT records created with correct amounts
# ---------------------------------------------------------------------------

def test_process_monthly_payroll_batch_draft():
    """
    HR processes the November 2026 payroll batch.
    Verifies that DRAFT records are created with the correct:
      • gross salary
      • total statutory deductions
      • LOP deduction  (1.5 unpaid days × daily-rate)
      • net salary
    """
    hr_token = get_token("hr@payroll.com", "Hr@123")

    req_payload = {
        "month": 11,
        "year": 2026,
        "payment_method": "BANK_TRANSFER",
        "remarks": "Standard November 2026 payroll run"
    }

    res = client.post(
        "/api/v1/payroll/process",
        headers={"Authorization": f"Bearer {hr_token}"},
        json=req_payload
    )
    assert res.status_code == 200, f"Process payroll failed: {res.json()}"
    batch = res.json()

    assert batch["payroll_batch_code"] == "PR-202611"
    assert batch["month"] == 11
    assert batch["year"] == 2026
    assert batch["total_employees_processed"] >= 2

    # --- Validate John Doe (EMP1001) ---
    john_rec = next(
        (r for r in batch["records"] if r["employee_code"] == "EMP1001"),
        None
    )
    assert john_rec is not None, "EMP1001 record not found in batch"
    assert john_rec["status"] == "DRAFT"
    assert float(john_rec["payable_days"]) == 30.0
    assert float(john_rec["gross_salary"]) == 9000.00
    assert float(john_rec["total_deductions"]) == 1400.00

    # 1 unexcused absence + 1 half-day = 1.5 unpaid days
    # Daily rate = 9000 / 30 = 300.00 → LOP = 300.00 × 1.5 = 450.00
    assert float(john_rec["unpaid_leaves"]) == 1.5
    assert float(john_rec["lop_deduction"]) == 450.00

    # Net = Gross − Deductions − LOP = 9000 − 1400 − 450 = 7150.00
    assert float(john_rec["net_salary"]) == 7150.00

    # Verify immutable detail snapshot contains key components
    detail_names = [d["component_name"] for d in john_rec["details"]]
    assert "Basic Salary" in detail_names
    assert "House Rent Allowance" in detail_names
    assert "Provident Fund" in detail_names


# ---------------------------------------------------------------------------
# Test 2: Admin approves a DRAFT record → APPROVED
# ---------------------------------------------------------------------------

def test_admin_approve_payroll_lifecycle():
    """
    Admin fetches November 2026 payroll records and approves John Doe's DRAFT.
    Verifies status transitions to APPROVED and approver username is recorded.
    """
    admin_token = get_token("admin@payroll.com", "Admin@123")

    # Fetch all November 2026 records
    records_res = client.get(
        "/api/v1/payroll/records?month=11&year=2026",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert records_res.status_code == 200
    records = records_res.json()
    assert len(records) >= 1, "No November 2026 payroll records found"

    john_rec = next(
        (r for r in records if r["employee_code"] == "EMP1001"),
        None
    )
    assert john_rec is not None, "EMP1001 record not in payroll list"
    assert john_rec["status"] == "DRAFT", \
        f"Expected DRAFT but got '{john_rec['status']}' – run test_process first"
    record_id = john_rec["id"]

    # Admin approves
    approve_res = client.patch(
        f"/api/v1/payroll/records/{record_id}/approve"
        "?remarks=Audited%20and%20approved%20by%20Admin",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approve_res.status_code == 200, f"Approve failed: {approve_res.json()}"
    approved_rec = approve_res.json()
    assert approved_rec["status"] == "APPROVED"
    assert approved_rec["approved_by_username"] == "admin"


# ---------------------------------------------------------------------------
# Test 3: Admin disburses APPROVED record → PAID
# ---------------------------------------------------------------------------

def test_admin_disburse_payroll_paid():
    """
    Admin fetches the APPROVED November 2026 record and marks it as PAID.
    Verifies status is PAID and payment_date is recorded.
    """
    admin_token = get_token("admin@payroll.com", "Admin@123")

    # Fetch only APPROVED records
    records_res = client.get(
        "/api/v1/payroll/records?month=11&year=2026&status=APPROVED",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert records_res.status_code == 200
    approved_records = records_res.json()
    assert len(approved_records) >= 1, \
        "No APPROVED records found – run test_admin_approve_payroll_lifecycle first"

    record_id = approved_records[0]["id"]

    pay_payload = {
        "status": "PAID",
        "payment_date": "2026-11-30",
        "remarks": "Direct bank transfer credited via SVB"
    }
    pay_res = client.patch(
        f"/api/v1/payroll/records/{record_id}/pay",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=pay_payload
    )
    assert pay_res.status_code == 200, f"Pay failed: {pay_res.json()}"
    paid_rec = pay_res.json()
    assert paid_rec["status"] == "PAID"
    assert paid_rec["payment_date"] == "2026-11-30"


# ---------------------------------------------------------------------------
# Test 4: Duplicate-lock – cannot reprocess finalized (PAID) records
# ---------------------------------------------------------------------------

def test_prevent_duplicate_payroll_when_finalized():
    """
    After at least one November 2026 record is PAID, attempting to reprocess
    the full November 2026 batch must return 409 Conflict with the
    'already finalized' message.
    """
    hr_token = get_token("hr@payroll.com", "Hr@123")

    req_payload = {
        "month": 11,
        "year": 2026,
        "payment_method": "BANK_TRANSFER"
    }

    res = client.post(
        "/api/v1/payroll/process",
        headers={"Authorization": f"Bearer {hr_token}"},
        json=req_payload
    )
    # Must fail with 409 Conflict because a PAID record exists for this period
    assert res.status_code == 409, f"Expected 409 but got {res.status_code}: {res.json()}"
    assert "already finalized" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 5: Employee views their own payroll via /me
# ---------------------------------------------------------------------------

def test_employee_view_own_payroll():
    """
    The employee linked to EMP1001 can retrieve their own payroll history.
    Verifies the net salary matches the expected value for November 2026.
    """
    emp_token = get_token("employee@payroll.com", "Employee@123")
    res = client.get(
        "/api/v1/payroll/me",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert res.status_code == 200
    my_records = res.json()
    assert len(my_records) >= 1, "Employee has no payroll records"
    nov_rec = next((r for r in my_records if r["month"] == 11 and r["year"] == 2026), None)
    assert nov_rec is not None, "November 2026 record not found for employee"
    assert nov_rec["employee_code"] == "EMP1001"
    assert float(nov_rec["net_salary"]) == 7150.00


# ---------------------------------------------------------------------------
# Test 6: RBAC – employees cannot initiate or approve payroll
# ---------------------------------------------------------------------------

def test_rbac_employee_cannot_process_or_approve():
    """
    Employees must receive 403 Forbidden when attempting:
      1. POST /payroll/process
      2. PATCH /payroll/records/{id}/approve
    """
    emp_token = get_token("employee@payroll.com", "Employee@123")

    # 1. Employee tries to initiate payroll processing
    proc_res = client.post(
        "/api/v1/payroll/process",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"month": 12, "year": 2026}
    )
    assert proc_res.status_code == 403, \
        f"Expected 403 but got {proc_res.status_code}"

    # 2. Employee tries to approve any payroll record
    appr_res = client.patch(
        "/api/v1/payroll/records/1/approve",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert appr_res.status_code == 403, \
        f"Expected 403 but got {appr_res.status_code}"
