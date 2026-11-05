"""
Payslip Service
===============
Orchestrates payslip generation, retrieval, and download-count tracking.
Delegates PDF rendering to ``payslip_pdf_service``.
"""

import os
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.payroll import Payroll, PayrollStatus
from app.models.payslip import Payslip
from app.models.employee import Employee
from app.schemas.payslip import PayslipResponse
from app.services.payslip_pdf_service import generate_payslip_pdf
from app.core.exceptions import (
    ResourceNotFoundException,
    DuplicateResourceException,
    PayrollException,
    PermissionDeniedException,
)

# Directory (relative to project root) where PDFs are stored
PAYSLIP_DIR = os.path.join("uploads", "payslips")


class PayslipService:

    # ------------------------------------------------------------------
    # Internal helper: build a PayslipResponse from an ORM object
    # ------------------------------------------------------------------
    @staticmethod
    def _format_response(ps: Payslip) -> PayslipResponse:
        emp  = ps.employee
        dept = emp.department.name       if emp and emp.department   else None
        desig = emp.designation.title    if emp and emp.designation  else None
        return PayslipResponse(
            id=ps.id,
            payslip_number=ps.payslip_number,
            payroll_id=ps.payroll_id,
            employee_id=ps.employee_id,
            employee_code=emp.employee_code if emp else None,
            employee_name=emp.full_name     if emp else None,
            department_name=dept,
            designation_title=desig,
            month=ps.month,
            year=ps.year,
            file_path=ps.file_path,
            download_count=ps.download_count,
            generated_at=ps.generated_at,
            updated_at=ps.updated_at,
        )

    # ------------------------------------------------------------------
    # Generate (or regenerate) a payslip PDF for a given payroll record
    # ------------------------------------------------------------------
    @staticmethod
    def generate_payslip(
        db: Session,
        payroll_id: int,
        company_name: str = "Acme Corporation Pvt. Ltd.",
        company_address: str = "123 Business Park, Tech City - 560001",
        company_email: str = "hr@acmecorp.com",
    ) -> PayslipResponse:
        """
        Generate (or regenerate) the PDF payslip for a payroll record.

        Rules:
        - The payroll record must be in APPROVED or PAID state.
        - If a Payslip row already exists (regeneration), the existing PDF
          file is overwritten and the DB row updated in-place.
        - Newly generated payslips are created in DRAFT payroll state only
          after admin approval (enforced here).
        """
        # 1. Load the payroll record
        payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
        if not payroll:
            raise ResourceNotFoundException("Payroll record", payroll_id)

        if payroll.status == PayrollStatus.DRAFT:
            raise PayrollException(
                "Payslips can only be generated for APPROVED or PAID payroll records. "
                f"Current status: '{payroll.status.value}'."
            )

        # 2. Build payslip number and output path
        emp: Employee = payroll.employee
        payslip_number = f"PS-{payroll.year}{payroll.month:02d}-{emp.employee_code}"
        filename       = f"{payslip_number}.pdf"
        output_path    = os.path.join(PAYSLIP_DIR, filename)

        # 3. Assemble the data dict expected by the PDF service
        payroll_data = {
            "employee_code":     emp.employee_code,
            "employee_name":     emp.full_name,
            "department_name":   emp.department.name     if emp.department  else "—",
            "designation_title": emp.designation.title   if emp.designation else "—",
            "date_of_joining":   emp.date_of_joining,
            "bank_name":         emp.bank_name,
            "masked_bank_account": emp.masked_bank_account,
            "month":             payroll.month,
            "year":              payroll.year,
            "payment_date":      payroll.payment_date,
            "payable_days":      payroll.payable_days,
            "present_days":      payroll.present_days,
            "paid_leaves":       payroll.paid_leaves,
            "unpaid_leaves":     payroll.unpaid_leaves,
            "gross_salary":      payroll.gross_salary,
            "total_deductions":  payroll.total_deductions,
            "lop_deduction":     payroll.lop_deduction,
            "net_salary":        payroll.net_salary,
            "details": [
                {
                    "component_name": d.component_name,
                    "component_type": d.component_type.value,
                    "amount":         d.amount,
                }
                for d in payroll.details
            ],
        }

        # 4. Render the PDF
        generate_payslip_pdf(
            payroll_data=payroll_data,
            output_path=output_path,
            company_name=company_name,
            company_address=company_address,
            company_email=company_email,
        )

        # 5. Upsert the Payslip DB row
        existing = db.query(Payslip).filter(Payslip.payroll_id == payroll_id).first()
        if existing:
            # Regeneration: update metadata, reset path
            existing.payslip_number = payslip_number
            existing.file_path      = output_path
            # download_count intentionally preserved
            db.commit()
            db.refresh(existing)
            return PayslipService._format_response(existing)
        else:
            ps = Payslip(
                payslip_number=payslip_number,
                payroll_id=payroll_id,
                employee_id=emp.id,
                month=payroll.month,
                year=payroll.year,
                file_path=output_path,
                download_count=0,
            )
            db.add(ps)
            db.commit()
            db.refresh(ps)
            return PayslipService._format_response(ps)

    # ------------------------------------------------------------------
    # List payslips (admin/HR see all; employee sees their own)
    # ------------------------------------------------------------------
    @staticmethod
    def list_payslips(
        db: Session,
        employee_id: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> List[PayslipResponse]:
        query = db.query(Payslip)
        if employee_id is not None:
            query = query.filter(Payslip.employee_id == employee_id)
        if month is not None:
            query = query.filter(Payslip.month == month)
        if year is not None:
            query = query.filter(Payslip.year == year)
        payslips = query.order_by(Payslip.year.desc(), Payslip.month.desc()).all()
        return [PayslipService._format_response(ps) for ps in payslips]

    # ------------------------------------------------------------------
    # Get a single payslip by ID; optionally enforce employee ownership
    # ------------------------------------------------------------------
    @staticmethod
    def get_payslip_by_id(
        db: Session,
        payslip_id: int,
        requesting_employee_id: Optional[int] = None,
    ) -> Payslip:
        ps = db.query(Payslip).filter(Payslip.id == payslip_id).first()
        if not ps:
            raise ResourceNotFoundException("Payslip", payslip_id)
        if requesting_employee_id is not None and ps.employee_id != requesting_employee_id:
            raise PermissionDeniedException(
                "You are not authorised to access another employee's payslip."
            )
        return ps

    # ------------------------------------------------------------------
    # Increment download counter and return the filesystem path
    # ------------------------------------------------------------------
    @staticmethod
    def record_download(db: Session, payslip_id: int) -> str:
        ps = db.query(Payslip).filter(Payslip.id == payslip_id).first()
        if not ps:
            raise ResourceNotFoundException("Payslip", payslip_id)
        ps.download_count += 1
        db.commit()
        return ps.file_path
