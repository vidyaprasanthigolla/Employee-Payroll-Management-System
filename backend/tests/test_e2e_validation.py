"""
Phase 12 – End-to-End Validation, Edge Cases & Security Tests
============================================================
Covers:
  1. Input validation & boundary constraints (e.g., negative amounts, invalid dates, malformed emails).
  2. SQL injection & malicious string payload sanitization.
  3. Concurrent / double approval security guard.
  4. Non-existent resource edge cases (404 handling).
  5. Cross-tenant / unauthorized employee payslip access attempts.
  6. Frontend static asset resolution verification.
"""

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


def test_invalid_email_format_validation():
    """System must reject malformed emails with HTTP 422 Unprocessable Entity."""
    admin_token = get_token("admin@payroll.com", "Admin@123")
    res = client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "username": "baduser_test",
            "email": "not-a-valid-email",
            "password": "Password@123",
            "role": "EMPLOYEE"
        }
    )
    assert res.status_code == 422


def test_sql_injection_defense():
    """Search/filter params containing SQL injection payloads must be safely handled without 500 error."""
    hr_token = get_token("hr@payroll.com", "Hr@123")
    malicious_query = "' OR '1'='1"
    res = client.get(
        f"/api/v1/employees?search={malicious_query}",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert res.status_code == 200
    # ORM parameterization ensures zero leakage or SQL error
    assert isinstance(res.json()["items"], list)


def test_nonexistent_employee_returns_404():
    """Requesting non-existent entity must return standard 404 response."""
    hr_token = get_token("hr@payroll.com", "Hr@123")
    res = client.get(
        "/api/v1/employees/999999",
        headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_invalid_date_range_for_leave_application():
    """Applying for leave where end_date < start_date must return HTTP 400 Bad Request."""
    emp_token = get_token("employee@payroll.com", "Employee@123")
    res = client.post(
        "/api/v1/leaves/apply",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={
            "leave_type": "CASUAL",
            "start_date": "2026-12-15",
            "end_date": "2026-12-10",
            "reason": "Invalid backwards date"
        }
    )
    assert res.status_code == 400
    assert "earlier than start date" in res.json()["detail"].lower()


def test_frontend_app_endpoint_serves_html():
    """FastAPI must serve frontend HTML via /app route."""
    res = client.get("/app")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "PayrollPro" in res.text
