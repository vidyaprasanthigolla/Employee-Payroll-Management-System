import time
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


def test_list_departments():
    token = get_token("hr@payroll.com", "Hr@123")
    res = client.get("/api/v1/departments", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    depts = res.json()
    assert len(depts) >= 4
    names = [d["name"] for d in depts]
    assert "Engineering" in names
    assert "Human Resources" in names


def test_create_and_duplicate_department():
    token = get_token("admin@payroll.com", "Admin@123")
    unique_name = f"Research & AI_{int(time.time() * 1000)}"

    # Create new department
    res = client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": unique_name, "description": "Antigravity frontier models & AI lab"}
    )
    assert res.status_code == 201
    assert res.json()["name"] == unique_name

    # Duplicate creation must return 409 Conflict
    dup_res = client.post(
        "/api/v1/departments",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": unique_name, "description": "Duplicate attempt"}
    )
    assert dup_res.status_code == 409


def test_list_designations_with_filter():
    token = get_token("admin@payroll.com", "Admin@123")
    # Fetch engineering dept id
    depts = client.get("/api/v1/departments", headers={"Authorization": f"Bearer {token}"}).json()
    eng_dept = next(d for d in depts if d["name"] == "Engineering")

    res = client.get(
        f"/api/v1/designations?department_id={eng_dept['id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    desigs = res.json()
    titles = [d["title"] for d in desigs]
    assert "Senior Software Engineer" in titles


def test_list_employees_pagination_and_search():
    token = get_token("hr@payroll.com", "Hr@123")
    res = client.get(
        "/api/v1/employees?page=1&page_size=10&search=John",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(emp["first_name"] == "John" for emp in data["items"])
    assert data["items"][0]["masked_bank_account"].startswith("****") or len(data["items"][0]["masked_bank_account"]) > 0


def test_employee_get_own_profile():
    # Login as Employee johndoe
    emp_token = get_token("employee@payroll.com", "Employee@123")
    res = client.get("/api/v1/employees/me", headers={"Authorization": f"Bearer {emp_token}"})
    assert res.status_code == 200
    emp = res.json()
    assert emp["employee_code"] == "EMP1001"
    assert emp["full_name"] == "John Doe"
    assert emp["masked_bank_account"] == "********1012"
    assert emp["department_name"] == "Engineering"


def test_employee_cannot_access_other_employee_profile():
    # Login as Employee johndoe (EMP1001)
    emp_token = get_token("employee@payroll.com", "Employee@123")

    # HR lists all employees to find another employee's ID (not EMP1001)
    hr_token = get_token("hr@payroll.com", "Hr@123")
    hr_res = client.get("/api/v1/employees?page_size=50", headers={"Authorization": f"Bearer {hr_token}"})
    other_emp = next((e for e in hr_res.json()["items"] if e["employee_code"] != "EMP1001"), None)
    assert other_emp is not None, "At least one other employee required for RBAC test"

    # John Doe attempts to view other employee's profile directly
    forbidden_res = client.get(
        f"/api/v1/employees/{other_emp['id']}",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert forbidden_res.status_code == 403
    assert "only authorized to view your own" in forbidden_res.json()["detail"]


def test_hr_create_employee_with_auto_login():
    token = get_token("hr@payroll.com", "Hr@123")
    unique_suffix = int(time.time() * 1000)

    # Get a department and designation
    depts = client.get("/api/v1/departments", headers={"Authorization": f"Bearer {token}"}).json()
    eng_dept = next(d for d in depts if d["name"] == "Engineering")
    desigs = client.get(f"/api/v1/designations?department_id={eng_dept['id']}", headers={"Authorization": f"Bearer {token}"}).json()

    new_emp_payload = {
        "first_name": "Robert",
        "last_name": "Miller",
        "phone": "+1 (555) 345-9876",
        "address": "12 Tech Square, Silicon Valley, CA",
        "date_of_birth": "1995-06-12",
        "gender": "MALE",
        "date_of_joining": "2024-01-15",
        "department_id": eng_dept["id"],
        "designation_id": desigs[0]["id"] if desigs else None,
        "employment_type": "FULL_TIME",
        "bank_name": "Wells Fargo",
        "bank_account_number": "554433221100",
        "ifsc_code": "WF0007890",
        "pan_number": f"PAN{unique_suffix % 10000000:07d}",
        "status": "ACTIVE",
        "create_login_account": True,
        "email": f"robert_{unique_suffix}@payroll.com",
        "password": "Robert@123"
    }

    res = client.post(
        "/api/v1/employees",
        headers={"Authorization": f"Bearer {token}"},
        json=new_emp_payload
    )
    assert res.status_code == 201
    created_emp = res.json()
    assert created_emp["first_name"] == "Robert"
    assert created_emp["employee_code"].startswith("EMP")
    assert created_emp["masked_bank_account"] == "********1100"

    # Verify that the newly created employee can now log in immediately
    new_emp_token = get_token(f"robert_{unique_suffix}@payroll.com", "Robert@123")
    assert new_emp_token is not None
