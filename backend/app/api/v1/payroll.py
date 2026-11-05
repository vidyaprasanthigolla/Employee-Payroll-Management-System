from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.payroll import PayrollStatus
from app.schemas.payroll import (
    PayrollProcessRequest,
    PayrollStatusUpdate,
    PayrollResponse,
    PayrollBatchSummary
)
from app.services.payroll_service import PayrollService
from app.services.employee_service import EmployeeService
from app.core.dependencies import (
    require_authenticated,
    require_hr_or_admin,
    require_admin
)
from app.core.exceptions import PermissionDeniedException

router = APIRouter(prefix="/payroll", tags=["Payroll Processing"])


@router.post("/process", response_model=PayrollBatchSummary, summary="Process monthly payroll batch (Admin and HR)")
def process_payroll(
    request: PayrollProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """
    Executes automated monthly salary calculation.
    Computes Gross Salary, Statutory Deductions, Attendance LOP deductions,
    and Net Salary. Initially stored in DRAFT status.
    """
    return PayrollService.process_payroll_batch(
        db=db,
        processor_id=current_user.id,
        request=request
    )


@router.get("/records", response_model=List[PayrollResponse], summary="Query payroll records (Admin and HR)")
def list_payroll_records(
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month"),
    year: Optional[int] = Query(None, ge=2000, description="Filter by year"),
    status: Optional[PayrollStatus] = Query(None, description="Filter by DRAFT, APPROVED, PAID, REJECTED"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    """Lists payroll records with flexible period, status, and department filtering."""
    return PayrollService.get_payroll_records(
        db=db,
        month=month,
        year=year,
        status=status,
        department_id=department_id,
        employee_id=employee_id
    )


@router.get("/me", response_model=List[PayrollResponse], summary="View personal payroll records (Employee)")
def get_my_payroll_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    """Allows an employee to view their finalized/approved salary records."""
    emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
    return PayrollService.get_payroll_records(db=db, employee_id=emp.id)


@router.get("/records/{payroll_id}", response_model=PayrollResponse, summary="Get details of specific payroll record")
def get_payroll_record(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated)
):
    record = PayrollService.get_payroll_by_id(db, payroll_id)
    if current_user.role == UserRole.EMPLOYEE:
        emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
        if record.employee_id != emp.id:
            raise PermissionDeniedException("You are only permitted to view your own payroll record.")
    return record


@router.patch("/records/{payroll_id}/approve", response_model=PayrollResponse, summary="Approve payroll record (Admin only)")
def approve_payroll_record(
    payroll_id: int,
    remarks: Optional[str] = Query(None, description="Approval notes"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Locks and approves a DRAFT payroll record. Restricted to Administrators."""
    return PayrollService.approve_payroll(
        db=db,
        payroll_id=payroll_id,
        approver_id=current_admin.id,
        remarks=remarks
    )


@router.patch("/records/{payroll_id}/pay", response_model=PayrollResponse, summary="Disburse and mark payroll as PAID (Admin only)")
def mark_payroll_as_paid(
    payroll_id: int,
    status_update: PayrollStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """Transitions APPROVED payroll record to PAID upon wage disbursement."""
    return PayrollService.mark_payroll_paid(
        db=db,
        payroll_id=payroll_id,
        payment_date=status_update.payment_date,
        remarks=status_update.remarks
    )
