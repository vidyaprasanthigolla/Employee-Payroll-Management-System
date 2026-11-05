"""
Phase 9 – Payslip PDF Generation Tests
=======================================
Covers:
  1. HR/Admin can generate a payslip for an APPROVED payroll record.
  2. Generated payslip metadata is returned correctly.
  3. The PDF file is physically created on disk.
  4. Regeneration overwrites the file and updates the DB row in-place.
  5. DRAFT payroll cannot have a payslip generated (must be APPROVED/PAID first).
  6. Employee can list their own payslips via /me.
  7. Employee download endpoint streams the PDF (200 OK, PDF content-type).
  8. RBAC: employee cannot generate payslips.
  9. Download increments the counter.

NOTE ON TEST ISOLATION
----------------------
This module-scoped fixture:
  • Wipes November 2026 payroll rows (and re-runs the batch from scratch) so
    these tests always start with a fresh DRAFT → APPROVED → PAID lifecycle.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.models.payroll import Payroll, PayrollDetail, PayrollStatus
from app.models.payslip import Payslip

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_token(username_or_email: str, password: str) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": username_or_email, "password": password}
    )
    assert res.status_code == 200, f"Login failed: {res.json()}"
    return res.json()["access_token"]


def admin_header():
    return {"Authorization": f"Bearer {get_token('admin@payroll.com', 'Admin@123')}"}


def hr_header():
    return {"Authorization": f"Bearer {get_token('hr@payroll.com', 'Hr@123')}"}


def emp_header():
    return {"Authorization": f"Bearer {get_token('employee@payroll.com', 'Employee@123')}"}


# ---------------------------------------------------------------------------
# Module-scoped fixture: ensure a clean, PAID Nov 2026 payroll exists
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def setup_approved_payroll():
    """
    Guarantees that at the start of this module:
      1. All November 2026 payslips are removed.
      2. All November 2026 payroll records are removed.
      3. A fresh November 2026 payroll batch is processed (creates DRAFT records).
      4. EMP1001's payroll record is approved → APPROVED.
      5. EMP1001's payroll record is then marked PAID.

    This gives us a valid PAID payroll record to generate payslips against,
    regardless of what prior test runs left in the shared SQLite DB.
    """
    db = next(get_db())
    try:
        # 1. Remove existing payslips for Nov 2026
        payroll_ids_nov = [
            r.id for r in db.query(Payroll).filter(
                Payroll.month == 11, Payroll.year == 2026
            ).all()
        ]
        if payroll_ids_nov:
            db.query(Payslip).filter(
                Payslip.payroll_id.in_(payroll_ids_nov)
            ).delete(synchronize_session=False)
            db.query(PayrollDetail).filter(
                PayrollDetail.payroll_id.in_(payroll_ids_nov)
            ).delete(synchronize_session=False)
        db.query(Payroll).filter(
            Payroll.month == 11, Payroll.year == 2026
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

    # 2. Process batch via API
    res = client.post(
        "/api/v1/payroll/process",
        headers=hr_header(),
        json={"month": 11, "year": 2026, "payment_method": "BANK_TRANSFER"}
    )
    assert res.status_code == 200, f"Payroll process failed: {res.json()}"
    batch = res.json()

    # Find EMP1001's record
    john = next(r for r in batch["records"] if r["employee_code"] == "EMP1001")
    record_id = john["id"]

    # 3. Approve it
    res2 = client.patch(
        f"/api/v1/payroll/records/{record_id}/approve",
        headers=admin_header()
    )
    assert res2.status_code == 200, f"Approve failed: {res2.json()}"

    # 4. Mark PAID
    res3 = client.patch(
        f"/api/v1/payroll/records/{record_id}/pay",
        headers=admin_header(),
        json={"status": "PAID", "payment_date": "2026-11-30"}
    )
    assert res3.status_code == 200, f"Pay failed: {res3.json()}"

    # Expose the payroll_id to tests via module-level variable
    pytest.john_payroll_id = record_id

    yield


# ---------------------------------------------------------------------------
# Test 1: Generate payslip for an APPROVED/PAID record (HR)
# ---------------------------------------------------------------------------

def test_hr_generate_payslip():
    """HR generates a payslip for the PAID November 2026 EMP1001 payroll."""
    res = client.post(
        f"/api/v1/payslips/generate/{pytest.john_payroll_id}",
        headers=hr_header(),
        json={}
    )
    assert res.status_code == 200, f"Generate failed: {res.json()}"
    ps = res.json()

    # Persist payslip ID for downstream tests
    pytest.john_payslip_id = ps["id"]

    assert ps["payslip_number"] == "PS-202611-EMP1001"
    assert ps["payroll_id"] == pytest.john_payroll_id
    assert ps["month"] == 11
    assert ps["year"] == 2026
    assert ps["download_count"] == 0
    assert "PS-202611-EMP1001.pdf" in ps["file_path"]
    assert ps["employee_code"] == "EMP1001"


# ---------------------------------------------------------------------------
# Test 2: PDF file is physically present on disk
# ---------------------------------------------------------------------------

def test_pdf_file_created_on_disk():
    """The PDF generated in Test 1 must exist as a real file."""
    # Retrieve the file path from the DB record
    res = client.get(
        f"/api/v1/payslips/{pytest.john_payslip_id}",
        headers=admin_header()
    )
    assert res.status_code == 200
    file_path = res.json()["file_path"]
    assert os.path.isfile(file_path), f"PDF not found on disk: {file_path}"
    assert os.path.getsize(file_path) > 1024, "PDF file is suspiciously small (<1 KB)"


# ---------------------------------------------------------------------------
# Test 3: Regeneration overwrites existing payslip (idempotent)
# ---------------------------------------------------------------------------

def test_regenerate_payslip_is_idempotent():
    """Calling generate a second time updates the row; download_count is kept."""
    # First, download once to have count=1
    client.get(
        f"/api/v1/payslips/{pytest.john_payslip_id}/download",
        headers=emp_header()
    )

    # Regenerate
    res = client.post(
        f"/api/v1/payslips/generate/{pytest.john_payroll_id}",
        headers=admin_header(),
        json={"company_name": "RegeneratedCo"}
    )
    assert res.status_code == 200, f"Regenerate failed: {res.json()}"
    ps = res.json()
    # Same payslip number and ID (not duplicated)
    assert ps["payslip_number"] == "PS-202611-EMP1001"
    assert ps["id"] == pytest.john_payslip_id
    # download_count preserved from before regeneration
    assert ps["download_count"] >= 1


# ---------------------------------------------------------------------------
# Test 4: Cannot generate payslip for a DRAFT payroll
# ---------------------------------------------------------------------------

def test_cannot_generate_payslip_for_draft_payroll():
    """
    Process a December 2026 batch (which will be DRAFT), then attempt to
    generate a payslip for it → must return 400 Bad Request.
    """
    # Create a December 2026 DRAFT payroll
    res = client.post(
        "/api/v1/payroll/process",
        headers=hr_header(),
        json={"month": 12, "year": 2026, "payment_method": "BANK_TRANSFER"}
    )
    assert res.status_code == 200
    batch = res.json()
    john_dec = next(
        (r for r in batch["records"] if r["employee_code"] == "EMP1001"),
        None
    )
    assert john_dec is not None
    draft_payroll_id = john_dec["id"]
    assert john_dec["status"] == "DRAFT"

    # Attempt to generate payslip → must fail
    res2 = client.post(
        f"/api/v1/payslips/generate/{draft_payroll_id}",
        headers=admin_header(),
        json={}
    )
    assert res2.status_code == 400, f"Expected 400, got {res2.status_code}: {res2.json()}"
    assert "DRAFT" in res2.json()["detail"]


# ---------------------------------------------------------------------------
# Test 5: Employee lists own payslips via /me
# ---------------------------------------------------------------------------

def test_employee_list_own_payslips():
    """Employee endpoint /me returns only their own payslips."""
    res = client.get("/api/v1/payslips/me", headers=emp_header())
    assert res.status_code == 200
    payslips = res.json()
    assert len(payslips) >= 1
    for ps in payslips:
        assert ps["employee_code"] == "EMP1001"


# ---------------------------------------------------------------------------
# Test 6: HR can list all payslips
# ---------------------------------------------------------------------------

def test_hr_list_all_payslips():
    """HR gets the full payslip list; must include EMP1001's November payslip."""
    res = client.get("/api/v1/payslips/", headers=hr_header())
    assert res.status_code == 200
    payslips = res.json()
    numbers = [ps["payslip_number"] for ps in payslips]
    assert "PS-202611-EMP1001" in numbers


# ---------------------------------------------------------------------------
# Test 7: Download PDF via API and verify Content-Type
# ---------------------------------------------------------------------------

def test_employee_download_payslip():
    """Employee can download their own payslip; response is application/pdf."""
    res = client.get(
        f"/api/v1/payslips/{pytest.john_payslip_id}/download",
        headers=emp_header()
    )
    assert res.status_code == 200
    assert "application/pdf" in res.headers.get("content-type", "")
    assert len(res.content) > 1024, "Downloaded PDF is too small"


# ---------------------------------------------------------------------------
# Test 8: Download increments the counter
# ---------------------------------------------------------------------------

def test_download_increments_counter():
    """Each /download call increments the download_count by 1."""
    # Get current count
    meta_before = client.get(
        f"/api/v1/payslips/{pytest.john_payslip_id}",
        headers=admin_header()
    ).json()
    count_before = meta_before["download_count"]

    # Download
    client.get(
        f"/api/v1/payslips/{pytest.john_payslip_id}/download",
        headers=admin_header()
    )

    meta_after = client.get(
        f"/api/v1/payslips/{pytest.john_payslip_id}",
        headers=admin_header()
    ).json()
    assert meta_after["download_count"] == count_before + 1


# ---------------------------------------------------------------------------
# Test 9: RBAC – employee cannot generate a payslip
# ---------------------------------------------------------------------------

def test_rbac_employee_cannot_generate_payslip():
    """Employees must receive 403 when calling the generate endpoint."""
    res = client.post(
        f"/api/v1/payslips/generate/{pytest.john_payroll_id}",
        headers=emp_header(),
        json={}
    )
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"
