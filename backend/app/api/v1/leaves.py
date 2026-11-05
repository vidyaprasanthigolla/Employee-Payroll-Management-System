from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.leave import LeaveStatus
from app.schemas.leave import (
    LeaveRequestCreate,
    LeaveReview,
    LeaveRequestResponse,
    LeaveBalanceResponse
)
from app.services.leave_service import LeaveService
from app.services.employee_service import EmployeeService
from app.core.dependencies import (
    require_authenticated,
    require_hr_or_admin
)
from app.core.exceptions import PermissionDeniedException

router = APIRouter(prefix="/leaves", tags=["Leaves"])


@router.post("/apply", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED, summary="Submit a leave application")
def apply_leave(
    leave_in: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """
    Submits a leave request. If employee_id is omitted or caller is an EMPLOYEE,
    it automatically associates with the caller's own employee record.
    """
    target_emp_id = leave_in.employee_id

    if current_user.role == UserRole.EMPLOYEE or not target_emp_id:
        emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
        target_emp_id = emp.id

    return LeaveService.apply_leave(db, target_emp_id, leave_in)


@router.get("/my-requests", response_model=List[LeaveRequestResponse], summary="Get current user's leave history")
def get_my_leave_requests(
    status: Optional[LeaveStatus] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Retrieves all past and pending leave applications submitted by the logged-in user."""
    emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
    return LeaveService.get_leave_requests(db, employee_id=emp.id, status=status)


@router.get("/my-balances", response_model=List[LeaveBalanceResponse], summary="Get current user's annual leave quotas")
def get_my_leave_balances(
    year: Optional[int] = Query(None, description="Calendar year (defaults to current year)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Returns available, used, and remaining leave quotas for the employee."""
    target_year = year or date.today().year
    emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
    return LeaveService.get_leave_balances(db, emp.id, target_year)


@router.get("/requests", response_model=List[LeaveRequestResponse], summary="List all leave requests across company (Admin and HR)")
def list_all_leave_requests(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    status: Optional[LeaveStatus] = Query(None, description="Filter by request status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Company-wide leave request inbox for HR and Administrators."""
    return LeaveService.get_leave_requests(db, employee_id=employee_id, status=status)


@router.patch("/requests/{request_id}/review", response_model=LeaveRequestResponse, summary="Approve or reject a leave request (Admin and HR)")
def review_leave_request(
    request_id: int,
    review_in: LeaveReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """
    Approves or rejects a pending leave application.
    When APPROVED, automatically deducts used days from quota and marks attendance as ON_LEAVE.
    """
    return LeaveService.review_leave_request(
        db=db,
        request_id=request_id,
        reviewer_id=current_user.id,
        review_in=review_in
    )


@router.get("/balances/{employee_id}", response_model=List[LeaveBalanceResponse], summary="Get leave quotas for any employee (Admin and HR)")
def get_employee_balances(
    employee_id: int,
    year: Optional[int] = Query(None, description="Calendar year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Enables HR and Admin to inspect any staff member's leave quotas."""
    target_year = year or date.today().year
    return LeaveService.get_leave_balances(db, employee_id, target_year)
