from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_
from app.models.leave import LeaveBalance, LeaveRequest, LeaveType, LeaveStatus
from app.models.employee import Employee
from app.models.attendance import Attendance, AttendanceStatus
from app.models.user import User
from app.schemas.leave import LeaveRequestCreate, LeaveReview, LeaveRequestResponse, LeaveBalanceResponse
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException, PayrollException


class LeaveService:
    DEFAULT_QUOTAS = {
        LeaveType.CASUAL: Decimal("12.0"),
        LeaveType.SICK: Decimal("10.0"),
        LeaveType.EARNED: Decimal("15.0"),
        LeaveType.UNPAID: Decimal("0.0"),
    }

    @staticmethod
    def initialize_employee_balances(db: Session, employee_id: int, year: int) -> List[LeaveBalance]:
        """Sets up default annual leave quotas for an employee for the given calendar year."""
        balances = []
        for l_type, quota in LeaveService.DEFAULT_QUOTAS.items():
            existing = db.query(LeaveBalance).filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year,
                LeaveBalance.leave_type == l_type
            ).first()

            if not existing:
                bal = LeaveBalance(
                    employee_id=employee_id,
                    year=year,
                    leave_type=l_type,
                    total_allocated=quota,
                    used=Decimal("0.0")
                )
                db.add(bal)
                balances.append(bal)
            else:
                balances.append(existing)

        db.commit()
        return balances

    @staticmethod
    def get_leave_balances(db: Session, employee_id: int, year: int) -> List[LeaveBalanceResponse]:
        balances = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.year == year
        ).all()

        if not balances:
            # Auto-initialize balances if missing for that year
            balances = LeaveService.initialize_employee_balances(db, employee_id, year)

        return [
            LeaveBalanceResponse(
                id=b.id,
                employee_id=b.employee_id,
                year=b.year,
                leave_type=b.leave_type,
                total_allocated=b.total_allocated,
                used=b.used,
                remaining=b.remaining
            )
            for b in balances
        ]

    @staticmethod
    def apply_leave(db: Session, employee_id: int, leave_in: LeaveRequestCreate) -> LeaveRequestResponse:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            raise ResourceNotFoundException("Employee", employee_id)

        if leave_in.end_date < leave_in.start_date:
            raise PayrollException("Leave end date cannot be earlier than start date.")

        # Calculate calendar leave days
        days = Decimal((leave_in.end_date - leave_in.start_date).days + 1)

        # Validate balance for paid leave types
        if leave_in.leave_type != LeaveType.UNPAID:
            year = leave_in.start_date.year
            bal = db.query(LeaveBalance).filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year,
                LeaveBalance.leave_type == leave_in.leave_type
            ).first()

            if not bal:
                LeaveService.initialize_employee_balances(db, employee_id, year)
                bal = db.query(LeaveBalance).filter(
                    LeaveBalance.employee_id == employee_id,
                    LeaveBalance.year == year,
                    LeaveBalance.leave_type == leave_in.leave_type
                ).first()

            if bal and bal.remaining < days:
                raise PayrollException(
                    f"Insufficient {leave_in.leave_type.value} leave balance. "
                    f"Requested: {days} days, Available: {bal.remaining} days."
                )

        req = LeaveRequest(
            employee_id=employee_id,
            leave_type=leave_in.leave_type,
            start_date=leave_in.start_date,
            end_date=leave_in.end_date,
            days=days,
            reason=leave_in.reason.strip(),
            status=LeaveStatus.PENDING
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        return LeaveService.format_request_response(req)

    @staticmethod
    def review_leave_request(db: Session, request_id: int, reviewer_id: int, review_in: LeaveReview) -> LeaveRequestResponse:
        req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
        if not req:
            raise ResourceNotFoundException("Leave request", request_id)

        if req.status != LeaveStatus.PENDING:
            raise PayrollException(f"This leave request is already finalized as '{req.status.value}'.")

        req.status = review_in.status
        req.reviewed_by = reviewer_id
        req.reviewed_at = datetime.utcnow()
        req.admin_remarks = review_in.admin_remarks.strip() if review_in.admin_remarks else None

        # If approved, deduct used balance and sync attendance calendar
        if review_in.status == LeaveStatus.APPROVED:
            # 1. Update leave balance
            if req.leave_type != LeaveType.UNPAID:
                year = req.start_date.year
                bal = db.query(LeaveBalance).filter(
                    LeaveBalance.employee_id == req.employee_id,
                    LeaveBalance.year == year,
                    LeaveBalance.leave_type == req.leave_type
                ).first()
                if bal:
                    bal.used += req.days

            # 2. Mark attendance as ON_LEAVE across the date range
            curr_date = req.start_date
            while curr_date <= req.end_date:
                existing_att = db.query(Attendance).filter(
                    Attendance.employee_id == req.employee_id,
                    Attendance.date == curr_date
                ).first()

                att_status = AttendanceStatus.ON_LEAVE
                if existing_att:
                    existing_att.status = att_status
                    existing_att.remarks = f"Leave approved: {req.leave_type.value}"
                else:
                    new_att = Attendance(
                        employee_id=req.employee_id,
                        date=curr_date,
                        status=att_status,
                        working_hours=Decimal("0.00"),
                        remarks=f"Leave approved: {req.leave_type.value}"
                    )
                    db.add(new_att)
                curr_date += timedelta(days=1)

        db.commit()
        db.refresh(req)
        return LeaveService.format_request_response(req)

    @staticmethod
    def get_leave_requests(
        db: Session,
        employee_id: Optional[int] = None,
        status: Optional[LeaveStatus] = None
    ) -> List[LeaveRequestResponse]:
        query = db.query(LeaveRequest).join(Employee, LeaveRequest.employee_id == Employee.id)

        if employee_id:
            query = query.filter(LeaveRequest.employee_id == employee_id)
        if status:
            query = query.filter(LeaveRequest.status == status)

        requests = query.order_by(LeaveRequest.id.desc()).all()
        return [LeaveService.format_request_response(r) for r in requests]

    @staticmethod
    def format_request_response(req: LeaveRequest) -> LeaveRequestResponse:
        reviewer_name = req.reviewer.username if req.reviewer else None
        emp_name = req.employee.full_name if req.employee else None
        emp_code = req.employee.employee_code if req.employee else None

        return LeaveRequestResponse(
            id=req.id,
            employee_id=req.employee_id,
            employee_name=emp_name,
            employee_code=emp_code,
            leave_type=req.leave_type,
            start_date=req.start_date,
            end_date=req.end_date,
            days=req.days,
            reason=req.reason,
            status=req.status,
            reviewed_by=req.reviewed_by,
            reviewed_by_username=reviewer_name,
            reviewed_at=req.reviewed_at,
            admin_remarks=req.admin_remarks,
            created_at=req.created_at,
            updated_at=req.updated_at
        )

    @staticmethod
    def get_unpaid_leave_days_in_month(db: Session, employee_id: int, month: int, year: int) -> Decimal:
        """
        Calculates total days of approved UNPAID leaves that fall within the given month.
        """
        approved_unpaid = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type == LeaveType.UNPAID,
            LeaveRequest.status == LeaveStatus.APPROVED
        ).all()

        unpaid_days = Decimal("0.0")
        for req in approved_unpaid:
            curr = req.start_date
            while curr <= req.end_date:
                if curr.month == month and curr.year == year:
                    unpaid_days += Decimal("1.0")
                curr += timedelta(days=1)

        return unpaid_days
