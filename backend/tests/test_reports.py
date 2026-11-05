"""
Phase 11 – Reports & Data Export Tests
======================================
Covers:
  1. Admin & HR can export Monthly Payroll Register to Excel (.xlsx).
  2. Admin & HR can export Monthly Payroll Summary to PDF (.pdf).
  3. Admin & HR can export Departmental Cost Breakdown to Excel (.xlsx).
  4. Admin & HR can export Statutory Deductions Compliance to Excel (.xlsx).
  5. RBAC: Employee cannot access compliance and financial export reports.
"""

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


def test_export_monthly_payroll_excel():
    hr_token = get_token("hr@payroll.com", "Hr@123")
    res = client.get(
        "/api/v1/reports/monthly-payroll/excel?month=11&year=2026",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
    assert len(res.content) > 1000


def test_export_monthly_payroll_pdf():
    admin_token = get_token("admin@payroll.com", "Admin@123")
    res = client.get(
        "/api/v1/reports/monthly-payroll/pdf?month=11&year=2026",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert len(res.content) > 1000


def test_export_department_payroll_excel():
    admin_token = get_token("admin@payroll.com", "Admin@123")
    res = client.get(
        "/api/v1/reports/department-payroll/excel?month=11&year=2026",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
    assert len(res.content) > 1000


def test_export_statutory_deductions_excel():
    hr_token = get_token("hr@payroll.com", "Hr@123")
    res = client.get(
        "/api/v1/reports/statutory-deductions/excel?month=11&year=2026",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
    assert len(res.content) > 1000


def test_rbac_employee_cannot_access_reports():
    emp_token = get_token("employee@payroll.com", "Employee@123")
    res = client.get(
        "/api/v1/reports/monthly-payroll/excel?month=11&year=2026",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert res.status_code == 403
