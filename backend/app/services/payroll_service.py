from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.payroll import Payroll, PayrollDetail, PayrollStatus, PaymentMethod
from app.models.employee import Employee, EmployeeStatus
from app.models.user import User
from app.schemas.payroll import (
    PayrollProcessRequest,
    PayrollStatusUpdate,
    PayrollResponse,
    PayrollDetailItem,
    PayrollBatchSummary
)
from app.services.salary_service import SalaryService
from app.services.attendance_service import AttendanceService
from app.services.payroll_calculator import PayrollCalculator
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException, PayrollException


class PayrollService:
    @staticmethod
    def format_payroll_response(record: Payroll) -> PayrollResponse:
        emp = record.employee
        dept_name = emp.department.name if emp and emp.department else None
        desig_title = emp.designation.title if emp and emp.designation else None
        proc_user = record.processor.username if record.processor else None
        appr_user = record.approver.username if record.approver else None

        detail_items = [
            PayrollDetailItem(
                id=d.id,
                component_name=d.component_name,
                component_type=d.component_type,
                amount=d.amount
            )
            for d in record.details
        ]

        return PayrollResponse(
            id=record.id,
            payroll_batch_code=record.payroll_batch_code,
            employee_id=record.employee_id,
            employee_code=emp.employee_code if emp else "",
            employee_name=emp.full_name if emp else "",
            department_name=dept_name,
            designation_title=desig_title,
            bank_name=emp.bank_name if emp else None,
            masked_bank_account=emp.masked_bank_account if emp else None,
            month=record.month,
            year=record.year,
            payable_days=record.payable_days,
            present_days=record.present_days,
            paid_leaves=record.paid_leaves,
            unpaid_leaves=record.unpaid_leaves,
            gross_salary=record.gross_salary,
            total_deductions=record.total_deductions,
            lop_deduction=record.lop_deduction,
            net_salary=record.net_salary,
            status=record.status,
            processed_by=record.processed_by,
            processed_by_username=proc_user,
            approved_by=record.approved_by,
            approved_by_username=appr_user,
            payment_date=record.payment_date,
            payment_method=record.payment_method,
            remarks=record.remarks,
            details=detail_items,
            created_at=record.created_at,
            updated_at=record.updated_at
        )

    @staticmethod
    def process_payroll_batch(
        db: Session,
        processor_id: int,
        request: PayrollProcessRequest
    ) -> PayrollBatchSummary:
        batch_code = f"PR-{request.year}{request.month:02d}"

        # 1. Identify target employees
        emp_query = db.query(Employee).filter(Employee.status == EmployeeStatus.ACTIVE)
        if request.employee_ids:
            emp_query = emp_query.filter(Employee.id.in_(request.employee_ids))

        target_employees = emp_query.all()
        if not target_employees:
            raise PayrollException("No active employees found matching the payroll processing criteria.")

        processed_records: List[Payroll] = []
        total_gross = Decimal("0.00")
        total_ded = Decimal("0.00")
        total_lop = Decimal("0.00")
        total_net = Decimal("0.00")

        for emp in target_employees:
            # Check existing record for period
            existing = db.query(Payroll).filter(
                Payroll.employee_id == emp.id,
                Payroll.month == request.month,
                Payroll.year == request.year
            ).first()

            # Guard against recalculating approved or paid records
            if existing and existing.status in [PayrollStatus.APPROVED, PayrollStatus.PAID]:
                raise DuplicateResourceException(
                    f"Payroll for employee {emp.employee_code} ({emp.full_name}) for {request.month:02d}/{request.year} "
                    f"is already finalized with status '{existing.status.value}' and cannot be reprocessed."
                )

            # Retrieve salary structure
            salary_breakdown = SalaryService.get_employee_salary_breakdown(db, emp.id)
            if not salary_breakdown.earnings:
                # Employee has no salary components assigned yet
                continue

            # Retrieve monthly attendance & leave metrics
            att_summary = AttendanceService.get_monthly_summary(
                db, employee_id=emp.id, month=request.month, year=request.year
            )

            # Calculate payroll amounts
            calc_result = PayrollCalculator.calculate_employee_payroll(
                employee_id=emp.id,
                month=request.month,
                year=request.year,
                salary_breakdown=salary_breakdown,
                attendance_summary=att_summary
            )

            if existing:
                # Update existing DRAFT record
                existing.payroll_batch_code = batch_code
                existing.payable_days = calc_result["payable_days"]
                existing.present_days = calc_result["present_days"]
                existing.paid_leaves = calc_result["paid_leaves"]
                existing.unpaid_leaves = calc_result["unpaid_leaves"]
                existing.gross_salary = calc_result["gross_salary"]
                existing.total_deductions = calc_result["total_deductions"]
                existing.lop_deduction = calc_result["lop_deduction"]
                existing.net_salary = calc_result["net_salary"]
                existing.processed_by = processor_id
                existing.payment_method = request.payment_method
                existing.remarks = request.remarks
                payroll_rec = existing
                # Clear past line items
                db.query(PayrollDetail).filter(PayrollDetail.payroll_id == existing.id).delete()
            else:
                payroll_rec = Payroll(
                    payroll_batch_code=batch_code,
                    employee_id=emp.id,
                    month=request.month,
                    year=request.year,
                    payable_days=calc_result["payable_days"],
                    present_days=calc_result["present_days"],
                    paid_leaves=calc_result["paid_leaves"],
                    unpaid_leaves=calc_result["unpaid_leaves"],
                    gross_salary=calc_result["gross_salary"],
                    total_deductions=calc_result["total_deductions"],
                    lop_deduction=calc_result["lop_deduction"],
                    net_salary=calc_result["net_salary"],
                    status=PayrollStatus.DRAFT,
                    processed_by=processor_id,
                    payment_method=request.payment_method,
                    remarks=request.remarks
                )
                db.add(payroll_rec)
                db.flush()

            # Insert immutable detail snapshot items
            for item in calc_result["details"]:
                detail_rec = PayrollDetail(
                    payroll_id=payroll_rec.id,
                    component_id=item["component_id"],
                    component_name=item["component_name"],
                    component_type=item["component_type"],
                    amount=item["amount"]
                )
                db.add(detail_rec)

            processed_records.append(payroll_rec)
            total_gross += calc_result["gross_salary"]
            total_ded += calc_result["total_deductions"]
            total_lop += calc_result["lop_deduction"]
            total_net += calc_result["net_salary"]

        db.commit()

        # Format responses
        responses = [PayrollService.format_payroll_response(r) for r in processed_records]
        return PayrollBatchSummary(
            payroll_batch_code=batch_code,
            month=request.month,
            year=request.year,
            total_employees_processed=len(responses),
            total_gross_disbursed=total_gross,
            total_statutory_deductions=total_ded,
            total_lop_deductions=total_lop,
            total_net_disbursed=total_net,
            records=responses
        )

    @staticmethod
    def approve_payroll(db: Session, payroll_id: int, approver_id: int, remarks: Optional[str] = None) -> PayrollResponse:
        record = db.query(Payroll).filter(Payroll.id == payroll_id).first()
        if not record:
            raise ResourceNotFoundException("Payroll record", payroll_id)

        if record.status != PayrollStatus.DRAFT:
            raise PayrollException(f"Only DRAFT payroll records can be approved. Current status: '{record.status.value}'.")

        record.status = PayrollStatus.APPROVED
        record.approved_by = approver_id
        if remarks:
            record.remarks = f"{record.remarks or ''}\n[Approved]: {remarks}".strip()

        db.commit()
        db.refresh(record)
        return PayrollService.format_payroll_response(record)

    @staticmethod
    def mark_payroll_paid(
        db: Session,
        payroll_id: int,
        payment_date: Optional[date] = None,
        payment_method: Optional[PaymentMethod] = None,
        remarks: Optional[str] = None
    ) -> PayrollResponse:
        record = db.query(Payroll).filter(Payroll.id == payroll_id).first()
        if not record:
            raise ResourceNotFoundException("Payroll record", payroll_id)

        if record.status != PayrollStatus.APPROVED:
            raise PayrollException(f"Only APPROVED payroll records can be marked as PAID. Current status: '{record.status.value}'.")

        record.status = PayrollStatus.PAID
        record.payment_date = payment_date or date.today()
        if payment_method:
            record.payment_method = payment_method
        if remarks:
            record.remarks = f"{record.remarks or ''}\n[Disbursed]: {remarks}".strip()

        db.commit()
        db.refresh(record)
        return PayrollService.format_payroll_response(record)

    @staticmethod
    def get_payroll_records(
        db: Session,
        month: Optional[int] = None,
        year: Optional[int] = None,
        status: Optional[PayrollStatus] = None,
        department_id: Optional[int] = None,
        employee_id: Optional[int] = None
    ) -> List[PayrollResponse]:
        query = db.query(Payroll).join(Employee, Payroll.employee_id == Employee.id)

        if month:
            query = query.filter(Payroll.month == month)
        if year:
            query = query.filter(Payroll.year == year)
        if status:
            query = query.filter(Payroll.status == status)
        if department_id:
            query = query.filter(Employee.department_id == department_id)
        if employee_id:
            query = query.filter(Payroll.employee_id == employee_id)

        records = query.order_by(Payroll.year.desc(), Payroll.month.desc(), Payroll.id.desc()).all()
        return [PayrollService.format_payroll_response(r) for r in records]

    @staticmethod
    def get_payroll_by_id(db: Session, payroll_id: int) -> PayrollResponse:
        record = db.query(Payroll).filter(Payroll.id == payroll_id).first()
        if not record:
            raise ResourceNotFoundException("Payroll record", payroll_id)
        return PayrollService.format_payroll_response(record)
