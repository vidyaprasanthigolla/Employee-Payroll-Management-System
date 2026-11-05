"""
Report API Endpoints
====================
Provides streaming endpoints for management and compliance exports:
  1. GET /reports/monthly-payroll/excel?month=11&year=2026
  2. GET /reports/monthly-payroll/pdf?month=11&year=2026
  3. GET /reports/department-payroll/excel?month=11&year=2026
  4. GET /reports/statutory-deductions/excel?month=11&year=2026
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.services.report_service import ReportService
from app.core.dependencies import require_hr_or_admin

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get("/monthly-payroll/excel", summary="Export Monthly Payroll Register to Excel (Admin & HR)")
def download_monthly_payroll_excel(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    excel_stream = ReportService.generate_monthly_payroll_excel(db, month=month, year=year)
    filename = f"Payroll_Register_{year}_{month:02d}.xlsx"
    return Response(
        content=excel_stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/monthly-payroll/pdf", summary="Export Monthly Payroll Summary Report to PDF (Admin & HR)")
def download_monthly_payroll_pdf(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    pdf_stream = ReportService.generate_monthly_payroll_pdf(db, month=month, year=year)
    filename = f"Payroll_Summary_{year}_{month:02d}.pdf"
    return Response(
        content=pdf_stream.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/department-payroll/excel", summary="Export Department Cost Report to Excel (Admin & HR)")
def download_department_payroll_excel(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    excel_stream = ReportService.generate_department_payroll_excel(db, month=month, year=year)
    filename = f"Department_Payroll_Report_{year}_{month:02d}.xlsx"
    return Response(
        content=excel_stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/statutory-deductions/excel", summary="Export Statutory Tax Compliance Report to Excel (Admin & HR)")
def download_statutory_deductions_excel(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_or_admin)
):
    excel_stream = ReportService.generate_statutory_deductions_excel(db, month=month, year=year)
    filename = f"Statutory_Compliance_{year}_{month:02d}.xlsx"
    return Response(
        content=excel_stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
