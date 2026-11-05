from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceResponse,
    MonthlyAttendanceSummary,
    BulkAttendanceCreate
)
from app.services.attendance_service import AttendanceService
from app.services.employee_service import EmployeeService
from app.core.dependencies import (
    require_authenticated,
    require_hr_or_admin
)
from app.core.exceptions import PermissionDeniedException

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED, summary="Mark or update attendance for an employee")
def mark_attendance(
    att_in: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """
    Records daily attendance. Employees can check in for themselves;
    HR/Admin can record attendance for any employee.
    """
    if current_user.role == UserRole.EMPLOYEE:
        emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
        if emp.id != att_in.employee_id:
            raise PermissionDeniedException("Employees can only log their own attendance.")

    return AttendanceService.mark_attendance(db, att_in)


@router.post("/bulk", summary="Bulk mark attendance (Admin and HR only)")
def bulk_mark_attendance(
    bulk_in: BulkAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Efficiently logs or updates daily attendance for multiple employees in one payload."""
    count = AttendanceService.bulk_mark_attendance(db, bulk_in)
    return {"message": f"Successfully processed {count} attendance records for date {bulk_in.date}."}


@router.get("", response_model=List[AttendanceResponse], summary="Filter attendance records (Admin and HR)")
def list_attendance(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Retrieves attendance history across the organization. Restricted to Admin & HR."""
    return AttendanceService.get_attendance_records(
        db=db,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/me", response_model=List[AttendanceResponse], summary="Get own attendance records")
def get_own_attendance(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Allows an authenticated user to fetch their personal daily attendance logs."""
    emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
    return AttendanceService.get_attendance_records(
        db=db,
        employee_id=emp.id,
        start_date=start_date,
        end_date=end_date
    )


@router.get("/summary/{employee_id}", response_model=MonthlyAttendanceSummary, summary="Get monthly attendance summary for payroll")
def get_monthly_attendance_summary(
    employee_id: int,
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    year: int = Query(..., ge=2000, description="Year (e.g. 2026)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """
    Computes present days, half days, absences, and total hours for a given month.
    Used directly by the Payroll Processing engine.
    """
    if current_user.role == UserRole.EMPLOYEE:
        emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
        if emp.id != employee_id:
            raise PermissionDeniedException("You are only permitted to view your own attendance summary.")

    return AttendanceService.get_monthly_summary(db, employee_id, month, year)
