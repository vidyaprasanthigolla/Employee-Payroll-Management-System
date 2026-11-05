from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.employee import EmployeeStatus
from app.models.user import User, UserRole
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeStatusUpdate,
    EmployeeResponse,
    EmployeePaginationResponse
)
from app.services.employee_service import EmployeeService
from app.core.dependencies import (
    get_current_active_user,
    require_hr_or_admin,
    require_admin,
    require_authenticated
)
from app.core.exceptions import PermissionDeniedException

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=EmployeePaginationResponse, summary="List employees with pagination and filters")
def list_employees(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name, code, phone, PAN, email"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    status: Optional[EmployeeStatus] = Query(None, description="Filter by employment status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Retrieves paginated employee master list. Restricted to Admin and HR."""
    return EmployeeService.get_employees(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        status=status
    )


@router.get("/me", response_model=EmployeeResponse, summary="Get own employee profile")
def get_own_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Allows any logged-in user to fetch their own linked employee master record."""
    emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
    return EmployeeService.format_employee_response(emp)


@router.get("/{emp_id}", response_model=EmployeeResponse, summary="Get employee details by ID")
def get_employee(
    emp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """
    Retrieves full employee details.
    Employees may only view their own profile; HR/Admin may view any.
    """
    emp = EmployeeService.get_employee_by_id(db, emp_id)
    if current_user.role == UserRole.EMPLOYEE and emp.user_id != current_user.id:
        raise PermissionDeniedException("You are only authorized to view your own employee record.")

    return EmployeeService.format_employee_response(emp)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED, summary="Create new employee")
def create_employee(
    emp_in: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Onboards a new employee into the system. Accessible by Admin and HR."""
    return EmployeeService.create_employee(db, emp_in)


@router.put("/{emp_id}", response_model=EmployeeResponse, summary="Update employee record")
def update_employee(
    emp_id: int,
    emp_in: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Updates demographic, designation, or banking details. Accessible by Admin and HR."""
    return EmployeeService.update_employee(db, emp_id, emp_in)


@router.patch("/{emp_id}/status", response_model=EmployeeResponse, summary="Update employment status")
def update_employee_status(
    emp_id: int,
    status_update: EmployeeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Updates status (e.g., ACTIVE, PROBATION, RESIGNED, TERMINATED)."""
    return EmployeeService.update_employee_status(db, emp_id, status_update.status)


@router.delete("/{emp_id}", summary="Delete employee (Admin only)")
def delete_employee(
    emp_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Removes employee master record. Restricted to Admin."""
    EmployeeService.delete_employee(db, emp_id)
    return {"message": f"Employee ID {emp_id} deleted successfully."}
