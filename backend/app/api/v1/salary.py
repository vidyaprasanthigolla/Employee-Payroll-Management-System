from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.salary import ComponentType
from app.schemas.salary import (
    SalaryComponentCreate,
    SalaryComponentUpdate,
    SalaryComponentResponse,
    SalaryStructureCreate,
    SalaryStructureUpdate,
    SalaryStructureResponse,
    AssignSalaryStructureRequest,
    EmployeeSalaryBreakdownResponse
)
from app.services.salary_service import SalaryService
from app.services.employee_service import EmployeeService
from app.core.dependencies import (
    require_authenticated,
    require_hr_or_admin,
    require_admin
)
from app.core.exceptions import PermissionDeniedException

router = APIRouter(prefix="/salary", tags=["Salary Structures & Components"])


# --- Salary Components Endpoints ---

@router.get("/components", response_model=List[SalaryComponentResponse], summary="List configurable salary components")
def list_components(
    type: Optional[ComponentType] = Query(None, description="Filter by EARNING or DEDUCTION"),
    is_active: Optional[bool] = Query(None, description="Filter active components"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Lists company earning and deduction components."""
    return SalaryService.get_components(db, comp_type=type, is_active=is_active)


@router.post("/components", response_model=SalaryComponentResponse, status_code=status.HTTP_201_CREATED, summary="Create a new salary component (Admin only)")
def create_component(
    comp_in: SalaryComponentCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Registers a new earning or deduction component."""
    return SalaryService.create_component(db, comp_in)


@router.put("/components/{comp_id}", response_model=SalaryComponentResponse, summary="Update a salary component (Admin only)")
def update_component(
    comp_id: int,
    comp_in: SalaryComponentUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    return SalaryService.update_component(db, comp_id, comp_in)


@router.delete("/components/{comp_id}", summary="Delete a salary component (Admin only)")
def delete_component(
    comp_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    SalaryService.delete_component(db, comp_id)
    return {"message": f"Component ID {comp_id} deleted successfully."}


# --- Salary Structure Templates ---

@router.get("/structures", response_model=List[SalaryStructureResponse], summary="List master salary structure grades")
def list_structures(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    return SalaryService.get_structures(db, is_active=is_active)


@router.post("/structures", response_model=SalaryStructureResponse, status_code=status.HTTP_201_CREATED, summary="Create salary structure grade (Admin only)")
def create_structure(
    struct_in: SalaryStructureCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    return SalaryService.create_structure(db, struct_in)


# --- Employee Salary Assignments ---

@router.get("/me", response_model=EmployeeSalaryBreakdownResponse, summary="View own active salary compensation structure")
def get_own_salary_structure(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Allows an employee to inspect their itemized monthly compensation package."""
    emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
    return SalaryService.get_employee_salary_breakdown(db, emp.id)


@router.get("/employees/{employee_id}", response_model=EmployeeSalaryBreakdownResponse, summary="Get employee salary breakdown (Admin and HR)")
def get_employee_salary(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Retrieves itemized salary breakdown for an employee."""
    if current_user.role == UserRole.EMPLOYEE:
        emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
        if emp.id != employee_id:
            raise PermissionDeniedException("You are only permitted to view your own salary structure.")

    return SalaryService.get_employee_salary_breakdown(db, employee_id)


@router.post("/employees/{employee_id}/assign", response_model=EmployeeSalaryBreakdownResponse, summary="Assign compensation package to employee (Admin and HR)")
def assign_employee_salary(
    employee_id: int,
    assign_in: AssignSalaryStructureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Configures earnings and deductions for an employee with automatic percentage calculation."""
    return SalaryService.assign_salary_structure(db, employee_id, assign_in)
