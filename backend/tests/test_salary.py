import time
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


def test_list_salary_components():
    token = get_token("hr@payroll.com", "Hr@123")
    res = client.get("/api/v1/salary/components", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    comps = res.json()
    assert len(comps) >= 11

    codes = [c["code"] for c in comps]
    assert "BASIC" in codes
    assert "HRA" in codes
    assert "PF" in codes
    assert "TDS" in codes


def test_create_custom_salary_component_and_duplicate_prevention():
    admin_token = get_token("admin@payroll.com", "Admin@123")
    unique_code = f"WFH_{int(time.time() * 1000) % 100000}"

    new_comp_payload = {
        "name": f"Remote WFH Stipend {unique_code}",
        "code": unique_code,
        "type": "EARNING",
        "calculation_type": "FLAT",
        "is_taxable": False,
        "is_statutory": False,
        "description": "Monthly remote home office and internet reimbursement"
    }

    # 1. Create component
    res = client.post(
        "/api/v1/salary/components",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=new_comp_payload
    )
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == unique_code
    assert data["type"] == "EARNING"

    # 2. Duplicate code must fail with 409 Conflict
    dup_res = client.post(
        "/api/v1/salary/components",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=new_comp_payload
    )
    assert dup_res.status_code == 409


def test_employee_get_own_salary_breakdown():
    emp_token = get_token("employee@payroll.com", "Employee@123")
    res = client.get("/api/v1/salary/me", headers={"Authorization": f"Bearer {emp_token}"})
    assert res.status_code == 200
    breakdown = res.json()

    assert breakdown["employee_code"] == "EMP1001"
    assert float(breakdown["gross_monthly_salary"]) == 9000.00
    assert float(breakdown["total_monthly_deductions"]) == 1400.00
    assert float(breakdown["net_monthly_salary"]) == 7600.00

    # Verify itemized calculations
    earn_codes = {e["component_code"]: float(e["amount"]) for e in breakdown["earnings"]}
    assert earn_codes["BASIC"] == 5000.00
    assert earn_codes["HRA"] == 2000.00   # 40% of 5000
    assert earn_codes["DA"] == 500.00     # 10% of 5000
    assert earn_codes["CONV"] == 300.00
    assert earn_codes["SPL_ALW"] == 1200.00

    ded_codes = {d["component_code"]: float(d["amount"]) for d in breakdown["deductions"]}
    assert ded_codes["PF"] == 600.00      # 12% of 5000
    assert ded_codes["PT"] == 200.00
    assert ded_codes["TDS"] == 600.00


def test_assign_salary_package_with_auto_percentage():
    hr_token = get_token("hr@payroll.com", "Hr@123")

    # Get components map
    comps_res = client.get("/api/v1/salary/components", headers={"Authorization": f"Bearer {hr_token}"})
    comp_map = {c["code"]: c["id"] for c in comps_res.json()}

    # Get Jane's employee ID
    emp_res = client.get("/api/v1/employees?search=Jane", headers={"Authorization": f"Bearer {hr_token}"})
    jane_id = emp_res.json()["items"][0]["id"]

    # Assign package where BASIC is 6,000, HRA is 30% (1,800), PF is 12% (720)
    assign_payload = {
        "effective_from": "2026-11-01",
        "components": [
            {"component_id": comp_map["BASIC"], "amount": 6000.00},
            {"component_id": comp_map["HRA"], "percentage": 30.00},
            {"component_id": comp_map["PF"], "percentage": 12.00},
            {"component_id": comp_map["TDS"], "amount": 400.00}
        ]
    }

    res = client.post(
        f"/api/v1/salary/employees/{jane_id}/assign",
        headers={"Authorization": f"Bearer {hr_token}"},
        json=assign_payload
    )
    assert res.status_code == 200
    breakdown = res.json()

    # Gross = 6,000 + 1,800 = 7,800
    assert float(breakdown["gross_monthly_salary"]) == 7800.00
    # Deductions = 720 (PF) + 400 (TDS) = 1,120
    assert float(breakdown["total_monthly_deductions"]) == 1120.00
    # Net = 7,800 - 1,120 = 6,680
    assert float(breakdown["net_monthly_salary"]) == 6680.00


def test_rbac_employee_cannot_create_component():
    emp_token = get_token("employee@payroll.com", "Employee@123")
    res = client.post(
        "/api/v1/salary/components",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={
            "name": "Hacker Bonus",
            "code": "HACK_BNS",
            "type": "EARNING",
            "calculation_type": "FLAT"
        }
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]
