import sys
import os
from datetime import date

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.designation import Designation
from app.models.employee import Employee, Gender, EmploymentType, EmployeeStatus
from app.core.security import get_password_hash


def init_db():
    print("=" * 60)
    print("INITIALIZING DATABASE & SEEDING MASTER DATA")
    print("=" * 60)

    # 1. Create all defined tables in the database
    print("Step 1: Creating database schema tables...")
    Base.metadata.create_all(bind=engine)
    print("-> Tables verified/created successfully.")

    db = SessionLocal()
    try:
        # 2. Seed default users
        print("\nStep 2: Checking and seeding default RBAC user accounts...")
        default_users = [
            {
                "username": "admin",
                "email": "admin@payroll.com",
                "password": "Admin@123",
                "role": UserRole.ADMIN,
            },
            {
                "username": "hrmanager",
                "email": "hr@payroll.com",
                "password": "Hr@123",
                "role": UserRole.HR,
            },
            {
                "username": "johndoe",
                "email": "employee@payroll.com",
                "password": "Employee@123",
                "role": UserRole.EMPLOYEE,
            },
            {
                "username": "janesmith",
                "email": "jane@payroll.com",
                "password": "Jane@123",
                "role": UserRole.EMPLOYEE,
            },
        ]

        user_map = {}
        for user_data in default_users:
            existing = db.query(User).filter(
                (User.email == user_data["email"]) | (User.username == user_data["username"])
            ).first()

            if not existing:
                new_user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                )
                db.add(new_user)
                db.flush()
                user_map[user_data["username"]] = new_user
                print(f"-> Created {user_data['role'].value} user: {user_data['email']}")
            else:
                user_map[user_data["username"]] = existing
                print(f"-> Existing user: {user_data['email']}")

        # 3. Seed default departments
        print("\nStep 3: Checking and seeding core departments...")
        depts_data = [
            {"name": "Engineering", "description": "Software architecture, development, and infrastructure"},
            {"name": "Human Resources", "description": "Talent acquisition, operations, and employee relations"},
            {"name": "Finance & Accounts", "description": "Corporate financial planning, payroll, and auditing"},
            {"name": "Sales & Marketing", "description": "Client acquisition, brand marketing, and PR"},
        ]

        dept_map = {}
        for d in depts_data:
            existing = db.query(Department).filter(Department.name == d["name"]).first()
            if not existing:
                new_dept = Department(name=d["name"], description=d["description"])
                db.add(new_dept)
                db.flush()
                dept_map[d["name"]] = new_dept
                print(f"-> Created Department: {d['name']}")
            else:
                dept_map[d["name"]] = existing
                print(f"-> Existing Department: {d['name']}")

        # 4. Seed default designations
        print("\nStep 4: Checking and seeding designations...")
        desig_data = [
            {"title": "Senior Software Engineer", "dept": "Engineering", "description": "Leads backend and API microservices"},
            {"title": "Frontend Engineer", "dept": "Engineering", "description": "Builds responsive client-side UI"},
            {"title": "HR Specialist", "dept": "Human Resources", "description": "Coordinates staff onboarding and attendance"},
            {"title": "Payroll Accountant", "dept": "Finance & Accounts", "description": "Executes monthly payroll and tax compliance"},
        ]

        desig_map = {}
        for des in desig_data:
            existing = db.query(Designation).filter(Designation.title == des["title"]).first()
            if not existing:
                dept_id = dept_map[des["dept"]].id if des["dept"] in dept_map else None
                new_desig = Designation(title=des["title"], department_id=dept_id, description=des["description"])
                db.add(new_desig)
                db.flush()
                desig_map[des["title"]] = new_desig
                print(f"-> Created Designation: {des['title']}")
            else:
                desig_map[des["title"]] = existing
                print(f"-> Existing Designation: {des['title']}")

        # 5. Seed default employee master records
        print("\nStep 5: Checking and seeding employee master profiles...")
        emp_john = db.query(Employee).filter(Employee.employee_code == "EMP1001").first()
        if not emp_john and "johndoe" in user_map:
            emp1 = Employee(
                employee_code="EMP1001",
                user_id=user_map["johndoe"].id,
                first_name="John",
                last_name="Doe",
                phone="+1 (555) 234-5678",
                address="452 Elm Street, Tech Corridor, CA",
                date_of_birth=date(1992, 4, 15),
                gender=Gender.MALE,
                date_of_joining=date(2022, 1, 10),
                department_id=dept_map["Engineering"].id,
                designation_id=desig_map["Senior Software Engineer"].id,
                employment_type=EmploymentType.FULL_TIME,
                bank_name="Silicon Valley Bank",
                bank_account_number="987654321012",
                ifsc_code="SVB0001234",
                pan_number="ABCDE1234F",
                status=EmployeeStatus.ACTIVE
            )
            db.add(emp1)
            print("-> Created Employee: EMP1001 (John Doe - Senior Software Engineer)")

        emp_jane = db.query(Employee).filter(Employee.employee_code == "EMP1002").first()
        if not emp_jane and "janesmith" in user_map:
            emp2 = Employee(
                employee_code="EMP1002",
                user_id=user_map["janesmith"].id,
                first_name="Jane",
                last_name="Smith",
                phone="+1 (555) 876-5432",
                address="789 Pine Ridge Road, CA",
                date_of_birth=date(1994, 8, 22),
                gender=Gender.FEMALE,
                date_of_joining=date(2023, 3, 1),
                department_id=dept_map["Finance & Accounts"].id,
                designation_id=desig_map["Payroll Accountant"].id,
                employment_type=EmploymentType.FULL_TIME,
                bank_name="Chase Morgan National",
                bank_account_number="112233445566",
                ifsc_code="CHAS009876",
                pan_number="WXYZ9876K",
                status=EmployeeStatus.ACTIVE
            )
            db.add(emp2)
            print("-> Created Employee: EMP1002 (Jane Smith - Payroll Accountant)")

        db.commit()

        # 6. Seed leave balances and initial attendance records
        print("\nStep 6: Checking and seeding leave balances and sample attendance...")
        from app.services.leave_service import LeaveService
        from app.services.attendance_service import AttendanceService
        from app.schemas.attendance import AttendanceCreate
        from app.models.attendance import AttendanceStatus
        from datetime import time

        all_emps = db.query(Employee).all()
        for e in all_emps:
            LeaveService.initialize_employee_balances(db, e.id, 2026)
            print(f"-> Initialized 2026 leave balances for: {e.employee_code} ({e.full_name})")

        # Seed sample attendance for November 2026 for John Doe (EMP1001)
        john = db.query(Employee).filter(Employee.employee_code == "EMP1001").first()
        if john:
            for day in range(1, 21):
                att_date = date(2026, 11, day)
                # Skip weekends
                if att_date.weekday() >= 5:
                    continue

                status = AttendanceStatus.PRESENT
                hours = 8.0
                if day == 10:
                    status = AttendanceStatus.HALF_DAY
                    hours = 4.0
                elif day == 16:
                    status = AttendanceStatus.ABSENT
                    hours = 0.0

                att_in = AttendanceCreate(
                    employee_id=john.id,
                    date=att_date,
                    status=status,
                    check_in=time(9, 0) if hours > 0 else None,
                    check_out=time(17, 0) if hours == 8.0 else (time(13, 0) if hours == 4.0 else None),
                    working_hours=hours,
                    remarks="Regular schedule" if status == AttendanceStatus.PRESENT else f"Status: {status.value}"
                )
                AttendanceService.mark_attendance(db, att_in)
            print("-> Seeded November 2026 attendance log for EMP1001 (John Doe)")

        # 7. Seed default salary components and assign packages to test employees
        print("\nStep 7: Checking and seeding salary components and employee packages...")
        from app.services.salary_service import SalaryService
        from app.schemas.salary import AssignSalaryStructureRequest, ComponentAssignmentItem
        from decimal import Decimal

        comps = SalaryService.seed_default_components(db)
        print(f"-> Verified/seeded {len(comps)} statutory and standard salary components.")
        comp_code_map = {c.code: c.id for c in comps}

        # Assign salary structure to EMP1001 (John Doe - Senior Software Engineer)
        if john:
            john_items = [
                ComponentAssignmentItem(component_id=comp_code_map["BASIC"], amount=Decimal("5000.00")),
                ComponentAssignmentItem(component_id=comp_code_map["HRA"], percentage=Decimal("40.00")),
                ComponentAssignmentItem(component_id=comp_code_map["DA"], percentage=Decimal("10.00")),
                ComponentAssignmentItem(component_id=comp_code_map["CONV"], amount=Decimal("300.00")),
                ComponentAssignmentItem(component_id=comp_code_map["SPL_ALW"], amount=Decimal("1200.00")),
                ComponentAssignmentItem(component_id=comp_code_map["PF"], percentage=Decimal("12.00")),
                ComponentAssignmentItem(component_id=comp_code_map["PT"], amount=Decimal("200.00")),
                ComponentAssignmentItem(component_id=comp_code_map["TDS"], amount=Decimal("600.00")),
            ]
            SalaryService.assign_salary_structure(
                db=db,
                employee_id=john.id,
                assign_in=AssignSalaryStructureRequest(effective_from=john.date_of_joining, components=john_items)
            )
            print("-> Assigned standard Engineering salary package to EMP1001 ($9,000 Gross / $7,600 Net)")

        # Assign salary structure to EMP1002 (Jane Smith - Payroll Accountant)
        jane = db.query(Employee).filter(Employee.employee_code == "EMP1002").first()
        if jane:
            jane_items = [
                ComponentAssignmentItem(component_id=comp_code_map["BASIC"], amount=Decimal("3500.00")),
                ComponentAssignmentItem(component_id=comp_code_map["HRA"], percentage=Decimal("40.00")),
                ComponentAssignmentItem(component_id=comp_code_map["CONV"], amount=Decimal("250.00")),
                ComponentAssignmentItem(component_id=comp_code_map["SPL_ALW"], amount=Decimal("600.00")),
                ComponentAssignmentItem(component_id=comp_code_map["PF"], percentage=Decimal("12.00")),
                ComponentAssignmentItem(component_id=comp_code_map["PT"], amount=Decimal("150.00")),
                ComponentAssignmentItem(component_id=comp_code_map["TDS"], amount=Decimal("300.00")),
            ]
            SalaryService.assign_salary_structure(
                db=db,
                employee_id=jane.id,
                assign_in=AssignSalaryStructureRequest(effective_from=jane.date_of_joining, components=jane_items)
            )
            print("-> Assigned Finance salary package to EMP1002 ($5,750 Gross / $4,880 Net)")

        print("\n[SUCCESS] Master data initialization and employee seeding completed.")
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Initialization failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
