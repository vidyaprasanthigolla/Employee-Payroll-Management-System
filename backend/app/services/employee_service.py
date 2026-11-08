import math
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.models.employee import Employee, EmployeeStatus
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.designation import Designation
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeePaginationResponse
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException, PayrollException


class EmployeeService:
    @staticmethod
    def generate_next_employee_code(db: Session) -> str:
        """
        Generates consecutive unique employee codes formatted as EMP1001, EMP1002, etc.
        """
        last_emp = db.query(Employee).order_by(desc(Employee.id)).first()
        if not last_emp:
            return "EMP1001"
        try:
            # Extract number from code if starts with EMP
            num = int(last_emp.employee_code.replace("EMP", ""))
            return f"EMP{num + 1}"
        except Exception:
            return f"EMP{1000 + last_emp.id + 1}"

    @staticmethod
    def format_employee_response(emp: Employee) -> EmployeeResponse:
        """Hydrates relational names and user email into response DTO."""
        dept_name = emp.department.name if emp.department else None
        desig_title = emp.designation.title if emp.designation else None
        user_email = emp.user.email if emp.user else None

        return EmployeeResponse(
            id=emp.id,
            employee_code=emp.employee_code,
            user_id=emp.user_id,
            email=user_email,
            first_name=emp.first_name,
            last_name=emp.last_name,
            full_name=emp.full_name,
            phone=emp.phone,
            address=emp.address,
            date_of_birth=emp.date_of_birth,
            gender=emp.gender,
            date_of_joining=emp.date_of_joining,
            department_id=emp.department_id,
            department_name=dept_name,
            designation_id=emp.designation_id,
            designation_title=desig_title,
            employment_type=emp.employment_type,
            bank_name=emp.bank_name,
            bank_account_number=emp.bank_account_number,
            masked_bank_account=emp.masked_bank_account,
            ifsc_code=emp.ifsc_code,
            pan_number=emp.pan_number,
            status=emp.status,
            created_at=emp.created_at,
            updated_at=emp.updated_at
        )

    @staticmethod
    def get_employees(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        department_id: Optional[int] = None,
        status: Optional[EmployeeStatus] = None
    ) -> EmployeePaginationResponse:
        query = db.query(Employee).join(User, Employee.user_id == User.id, isouter=True)

        if department_id:
            query = query.filter(Employee.department_id == department_id)

        if status:
            query = query.filter(Employee.status == status)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Employee.employee_code.ilike(term),
                    Employee.first_name.ilike(term),
                    Employee.last_name.ilike(term),
                    Employee.phone.ilike(term),
                    Employee.pan_number.ilike(term),
                    User.email.ilike(term)
                )
            )

        total = query.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        offset = (page - 1) * page_size
        employees = query.order_by(Employee.id.desc()).offset(offset).limit(page_size).all()

        items = [EmployeeService.format_employee_response(emp) for emp in employees]
        return EmployeePaginationResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=items
        )

    @staticmethod
    def get_employee_by_id(db: Session, employee_id: int) -> Employee:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            raise ResourceNotFoundException("Employee", employee_id)
        return emp

    @staticmethod
    def get_employee_by_user_id(db: Session, user_id: int) -> Employee:
        emp = db.query(Employee).filter(Employee.user_id == user_id).first()
        if not emp:
            raise ResourceNotFoundException("Employee profile for user", user_id)
        return emp

    @staticmethod
    def create_employee(db: Session, emp_in: EmployeeCreate) -> EmployeeResponse:
        # 1. Resolve or create associated user account
        user_id = emp_in.user_id

        if emp_in.create_login_account:
            if not emp_in.email or not emp_in.password:
                raise PayrollException("Email and password are required to create a login account.")
            # Auto-generate a clean username
            base_username = emp_in.email.split("@")[0].lower()
            username = base_username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1

            new_user = AuthService.create_user(
                db=db,
                user_in=UserCreate(
                    username=username,
                    email=emp_in.email,
                    password=emp_in.password,
                    role=UserRole.EMPLOYEE,
                    is_active=True
                )
            )
            user_id = new_user.id
        elif not user_id:
            raise PayrollException("Either provide an existing user_id or set create_login_account=True with email and password.")

        # Check if user is already linked to an employee
        existing_emp = db.query(Employee).filter(Employee.user_id == user_id).first()
        if existing_emp:
            raise DuplicateResourceException(f"User account ID {user_id} is already linked to employee {existing_emp.employee_code}.")

        # Validate PAN uniqueness
        existing_pan = db.query(Employee).filter(
            Employee.pan_number == emp_in.pan_number.strip().upper()
        ).first()
        if existing_pan:
            raise DuplicateResourceException(f"An employee with PAN '{emp_in.pan_number}' already exists ({existing_pan.employee_code}).")

        # Validate department and designation
        if emp_in.department_id:
            dept = db.query(Department).filter(Department.id == emp_in.department_id).first()
            if not dept:
                raise ResourceNotFoundException("Department", emp_in.department_id)

        if emp_in.designation_id:
            desig = db.query(Designation).filter(Designation.id == emp_in.designation_id).first()
            if not desig:
                raise ResourceNotFoundException("Designation", emp_in.designation_id)

        # Generate unique code
        emp_code = EmployeeService.generate_next_employee_code(db)

        emp = Employee(
            employee_code=emp_code,
            user_id=user_id,
            first_name=emp_in.first_name.strip(),
            last_name=emp_in.last_name.strip(),
            phone=emp_in.phone.strip(),
            address=emp_in.address.strip() if emp_in.address else None,
            date_of_birth=emp_in.date_of_birth,
            gender=emp_in.gender,
            date_of_joining=emp_in.date_of_joining,
            department_id=emp_in.department_id,
            designation_id=emp_in.designation_id,
            employment_type=emp_in.employment_type,
            bank_name=emp_in.bank_name.strip(),
            bank_account_number=emp_in.bank_account_number.strip(),
            ifsc_code=emp_in.ifsc_code.strip().upper(),
            pan_number=emp_in.pan_number.strip().upper(),
            status=emp_in.status
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        return EmployeeService.format_employee_response(emp)

    @staticmethod
    def update_employee(db: Session, employee_id: int, emp_in: EmployeeUpdate) -> EmployeeResponse:
        emp = EmployeeService.get_employee_by_id(db, employee_id)

        # Update fields if provided
        for field, value in emp_in.model_dump(exclude_unset=True).items():
            if field == "pan_number" and value:
                clean_pan = value.strip().upper()
                existing = db.query(Employee).filter(
                    Employee.pan_number == clean_pan,
                    Employee.id != employee_id
                ).first()
                if existing:
                    raise DuplicateResourceException(f"PAN '{clean_pan}' is already registered to employee {existing.employee_code}.")
                setattr(emp, field, clean_pan)
            elif field == "ifsc_code" and value:
                setattr(emp, field, value.strip().upper())
            elif isinstance(value, str):
                setattr(emp, field, value.strip())
            else:
                setattr(emp, field, value)

        db.commit()
        db.refresh(emp)
        return EmployeeService.format_employee_response(emp)

    @staticmethod
    def update_employee_status(db: Session, employee_id: int, status: EmployeeStatus) -> EmployeeResponse:
        emp = EmployeeService.get_employee_by_id(db, employee_id)
        emp.status = status
        db.commit()
        db.refresh(emp)
        return EmployeeService.format_employee_response(emp)

    @staticmethod
    def delete_employee(db: Session, employee_id: int) -> bool:
        emp = EmployeeService.get_employee_by_id(db, employee_id)
        db.delete(emp)
        db.commit()
        return True
    @staticmethod
    def update_employee_name(
        db: Session,
        employee_id: int,
        first_name: str,
        last_name: str
    ) -> EmployeeResponse:

        emp = EmployeeService.get_employee_by_id(db, employee_id)

        emp.first_name = first_name.strip()
        emp.last_name = last_name.strip()

        db.commit()
        db.refresh(emp)

        return EmployeeService.format_employee_response(emp)