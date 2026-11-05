import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_
from app.models.attendance import Attendance, AttendanceStatus
from app.models.employee import Employee
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceResponse,
    MonthlyAttendanceSummary,
    BulkAttendanceCreate
)
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException, PayrollException


class AttendanceService:
    @staticmethod
    def calculate_hours(check_in, check_out) -> Decimal:
        """Calculates duration in decimal hours between check_in and check_out times."""
        if not check_in or not check_out:
            return Decimal("0.00")
        today = date.today()
        dt_in = datetime.combine(today, check_in)
        dt_out = datetime.combine(today, check_out)
        if dt_out < dt_in:
            dt_out += timedelta(days=1)
        diff_hours = (dt_out - dt_in).total_seconds() / 3600.0
        return Decimal(f"{diff_hours:.2f}")

    @staticmethod
    def mark_attendance(db: Session, att_in: AttendanceCreate) -> AttendanceResponse:
        # Verify employee exists
        emp = db.query(Employee).filter(Employee.id == att_in.employee_id).first()
        if not emp:
            raise ResourceNotFoundException("Employee", att_in.employee_id)

        # Check existing record for that date
        existing = db.query(Attendance).filter(
            Attendance.employee_id == att_in.employee_id,
            Attendance.date == att_in.date
        ).first()

        hours = att_in.working_hours
        if (hours is None or hours == Decimal("0.00")) and att_in.check_in and att_in.check_out:
            hours = AttendanceService.calculate_hours(att_in.check_in, att_in.check_out)

        if existing:
            existing.status = att_in.status
            existing.check_in = att_in.check_in
            existing.check_out = att_in.check_out
            existing.working_hours = hours or Decimal("0.00")
            existing.remarks = att_in.remarks
            db.commit()
            db.refresh(existing)
            record = existing
        else:
            record = Attendance(
                employee_id=att_in.employee_id,
                date=att_in.date,
                status=att_in.status,
                check_in=att_in.check_in,
                check_out=att_in.check_out,
                working_hours=hours or Decimal("0.00"),
                remarks=att_in.remarks
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        return AttendanceResponse(
            id=record.id,
            employee_id=record.employee_id,
            employee_code=emp.employee_code,
            employee_name=emp.full_name,
            date=record.date,
            status=record.status,
            check_in=record.check_in,
            check_out=record.check_out,
            working_hours=record.working_hours,
            remarks=record.remarks,
            created_at=record.created_at,
            updated_at=record.updated_at
        )

    @staticmethod
    def bulk_mark_attendance(db: Session, bulk_in: BulkAttendanceCreate) -> int:
        count = 0
        for item in bulk_in.records:
            att_create = AttendanceCreate(
                employee_id=item.employee_id,
                date=bulk_in.date,
                status=item.status,
                check_in=item.check_in,
                check_out=item.check_out,
                working_hours=item.working_hours,
                remarks=item.remarks
            )
            AttendanceService.mark_attendance(db, att_create)
            count += 1
        return count

    @staticmethod
    def get_attendance_records(
        db: Session,
        employee_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[AttendanceResponse]:
        query = db.query(Attendance).join(Employee, Attendance.employee_id == Employee.id)

        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)
        if start_date:
            query = query.filter(Attendance.date >= start_date)
        if end_date:
            query = query.filter(Attendance.date <= end_date)

        records = query.order_by(Attendance.date.desc()).all()
        return [
            AttendanceResponse(
                id=r.id,
                employee_id=r.employee_id,
                employee_code=r.employee.employee_code,
                employee_name=r.employee.full_name,
                date=r.date,
                status=r.status,
                check_in=r.check_in,
                check_out=r.check_out,
                working_hours=r.working_hours,
                remarks=r.remarks,
                created_at=r.created_at,
                updated_at=r.updated_at
            )
            for r in records
        ]

    @staticmethod
    def get_monthly_summary(db: Session, employee_id: int, month: int, year: int) -> MonthlyAttendanceSummary:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            raise ResourceNotFoundException("Employee", employee_id)

        total_calendar_days = calendar.monthrange(year, month)[1]

        records = db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            extract("month", Attendance.date) == month,
            extract("year", Attendance.date) == year
        ).all()

        present_days = 0.0
        half_days = 0.0
        absent_days = 0.0
        leave_days = 0.0
        holiday_days = 0.0
        total_hours = Decimal("0.00")

        for r in records:
            total_hours += r.working_hours
            if r.status == AttendanceStatus.PRESENT:
                present_days += 1.0
            elif r.status == AttendanceStatus.HALF_DAY:
                half_days += 1.0
            elif r.status == AttendanceStatus.ABSENT:
                absent_days += 1.0
            elif r.status == AttendanceStatus.ON_LEAVE:
                leave_days += 1.0
            elif r.status == AttendanceStatus.HOLIDAY:
                holiday_days += 1.0

        effective_present = present_days + (0.5 * half_days)

        # Unpaid days calculation from unexcused absence & half days
        # (Loss of Pay = absent + 0.5 * half_days)
        unpaid_days = absent_days + (0.5 * half_days)

        return MonthlyAttendanceSummary(
            employee_id=emp.id,
            employee_code=emp.employee_code,
            employee_name=emp.full_name,
            month=month,
            year=year,
            total_calendar_days=total_calendar_days,
            present_days=present_days,
            half_days=half_days,
            absent_days=absent_days,
            leave_days=leave_days,
            holiday_days=holiday_days,
            effective_present_days=effective_present,
            unpaid_leave_days=unpaid_days,
            total_working_hours=float(total_hours)
        )
