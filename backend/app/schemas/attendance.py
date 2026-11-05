from datetime import date, time, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.models.attendance import AttendanceStatus


class AttendanceBase(BaseModel):
    employee_id: int
    date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    working_hours: Optional[Decimal] = Decimal("0.00")
    remarks: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    working_hours: Optional[Decimal] = None
    remarks: Optional[str] = None


class AttendanceResponse(AttendanceBase):
    id: int
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonthlyAttendanceSummary(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    month: int
    year: int
    total_calendar_days: int
    present_days: float
    half_days: float
    absent_days: float
    leave_days: float
    holiday_days: float
    effective_present_days: float
    unpaid_leave_days: float
    total_working_hours: float


class BulkAttendanceItem(BaseModel):
    employee_id: int
    status: AttendanceStatus = AttendanceStatus.PRESENT
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    working_hours: Optional[Decimal] = Decimal("8.00")
    remarks: Optional[str] = None


class BulkAttendanceCreate(BaseModel):
    date: date
    records: List[BulkAttendanceItem]
