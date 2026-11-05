"""
Payslip API Endpoints
=====================

POST  /payslips/generate/{payroll_id}  → Generate (or regenerate) payslip PDF  [Admin, HR]
GET   /payslips/                        → List all payslips                      [Admin, HR]
GET   /payslips/me                      → List logged-in employee's payslips     [Employee]
GET   /payslips/{payslip_id}            → Get metadata for one payslip           [Admin, HR, Employee (own only)]
GET   /payslips/{payslip_id}/download   → Stream the PDF file                   [Admin, HR, Employee (own only)]
"""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.payslip import PayslipResponse, PayslipGenerateRequest
from app.services.payslip_service import PayslipService
from app.services.employee_service import EmployeeService
from app.core.dependencies import require_authenticated, require_hr_or_admin
from app.core.exceptions import ResourceNotFoundException

router = APIRouter(prefix="/payslips", tags=["Payslips"])


# ---------------------------------------------------------------------------
# 1. Generate payslip PDF for a payroll record (Admin / HR only)
# ---------------------------------------------------------------------------
@router.post(
    "/generate/{payroll_id}",
    response_model=PayslipResponse,
    summary="Generate or regenerate a payslip PDF (Admin / HR)"
)
def generate_payslip(
    payroll_id: int,
    body: PayslipGenerateRequest = Body(default=PayslipGenerateRequest()),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """
    Renders a professional PDF payslip for the specified payroll record.

    - The payroll record **must** be in ``APPROVED`` or ``PAID`` state.
    - If a payslip already exists for this payroll record, it is **regenerated**
      (the PDF is overwritten; the download count is preserved).
    - The PDF is saved to ``uploads/payslips/PS-YYYYMM-EMPCODE.pdf``.
    """
    return PayslipService.generate_payslip(
        db=db,
        payroll_id=payroll_id,
        company_name=body.company_name,
        company_address=body.company_address,
        company_email=body.company_email,
    )


# ---------------------------------------------------------------------------
# 2. List all payslips with optional filters (Admin / HR only)
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=List[PayslipResponse],
    summary="List all payslips with optional filters (Admin / HR)"
)
def list_all_payslips(
    employee_id: Optional[int] = Query(None, description="Filter by employee DB ID"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month"),
    year: Optional[int] = Query(None, ge=2000, description="Filter by year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin),
):
    """Returns payslip metadata records; use ``/download`` to fetch the actual PDF."""
    return PayslipService.list_payslips(db=db, employee_id=employee_id, month=month, year=year)


# ---------------------------------------------------------------------------
# 3. Employee self-service: list own payslips
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=List[PayslipResponse],
    summary="List your own payslips (Employee self-service)"
)
def list_my_payslips(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """Returns only the payslips belonging to the currently logged-in employee."""
    emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
    return PayslipService.list_payslips(
        db=db, employee_id=emp.id, month=month, year=year
    )


# ---------------------------------------------------------------------------
# 4. Get metadata for a single payslip
# ---------------------------------------------------------------------------
@router.get(
    "/{payslip_id}",
    response_model=PayslipResponse,
    summary="Get payslip metadata by ID"
)
def get_payslip(
    payslip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Admin / HR can retrieve any payslip.
    Employees can only retrieve their own payslip (403 otherwise).
    """
    if current_user.role == UserRole.EMPLOYEE:
        emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
        ps = PayslipService.get_payslip_by_id(
            db, payslip_id, requesting_employee_id=emp.id
        )
    else:
        ps = PayslipService.get_payslip_by_id(db, payslip_id)

    from app.schemas.payslip import PayslipResponse as PSR
    return PayslipService._format_response(ps)


# ---------------------------------------------------------------------------
# 5. Download the actual PDF file
# ---------------------------------------------------------------------------
@router.get(
    "/{payslip_id}/download",
    summary="Download payslip PDF",
    response_class=FileResponse,
)
def download_payslip(
    payslip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated),
):
    """
    Streams the payslip PDF file.

    - Admin / HR can download any employee's payslip.
    - Employees can only download their own payslip.
    - Each successful download increments the ``download_count`` counter.
    """
    if current_user.role == UserRole.EMPLOYEE:
        emp = EmployeeService.get_employee_by_user_id(db, current_user.id)
        ps = PayslipService.get_payslip_by_id(
            db, payslip_id, requesting_employee_id=emp.id
        )
    else:
        ps = PayslipService.get_payslip_by_id(db, payslip_id)

    # Verify file exists on disk
    if not os.path.isfile(ps.file_path):
        raise ResourceNotFoundException("Payslip PDF file", ps.file_path)

    # Increment download counter
    PayslipService.record_download(db, payslip_id)

    return FileResponse(
        path=ps.file_path,
        media_type="application/pdf",
        filename=os.path.basename(ps.file_path),
    )
