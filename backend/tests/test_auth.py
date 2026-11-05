import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_admin_login_success():
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin@payroll.com", "password": "Admin@123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "ADMIN"
    assert data["email"] == "admin@payroll.com"


def test_hr_login_success():
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "hr@payroll.com", "password": "Hr@123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "HR"


def test_employee_login_success():
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "employee@payroll.com", "password": "Employee@123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "EMPLOYEE"


def test_login_invalid_password():
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin@payroll.com", "password": "WrongPassword!"}
    )
    assert response.status_code == 401
    assert "Incorrect" in response.json()["detail"]


def test_get_current_user_profile():
    # Login as Admin first
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin@payroll.com", "password": "Admin@123"}
    )
    token = login_res.json()["access_token"]

    # Call /me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "admin@payroll.com"
    assert me_data["role"] == "ADMIN"


def test_rbac_admin_route_forbidden_for_employee():
    # Login as Employee
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "employee@payroll.com", "password": "Employee@123"}
    )
    emp_token = login_res.json()["access_token"]

    # Attempt to call Admin-only registration endpoint
    headers = {"Authorization": f"Bearer {emp_token}"}
    reg_res = client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "Password@123",
            "role": "EMPLOYEE"
        }
    )
    # Must be 403 Forbidden due to RBAC RoleChecker
    assert reg_res.status_code == 403
    assert "Access denied" in reg_res.json()["detail"]


def test_admin_can_register_new_user():
    # Login as Admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin@payroll.com", "password": "Admin@123"}
    )
    admin_token = login_res.json()["access_token"]

    unique_suffix = int(time.time() * 1000)
    headers = {"Authorization": f"Bearer {admin_token}"}
    reg_res = client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={
            "username": f"auditor_{unique_suffix}",
            "email": f"auditor_{unique_suffix}@payroll.com",
            "password": "Auditor@123",
            "role": "HR"
        }
    )
    assert reg_res.status_code == 201
    new_user = reg_res.json()
    assert new_user["username"] == f"auditor_{unique_suffix}"
    assert new_user["role"] == "HR"
