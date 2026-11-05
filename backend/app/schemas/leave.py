from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.models.leave import LeaveType, LeaveStatus


class LeaveBalanceResponse(BaseModel):
    id: int
    employee_id: int
    year: int
    leave_type: LeaveType
    total_allocated: Decimal
    used: Decimal
    remaining: Decimal

    model_config = ConfigDict(from_attributes=True)


class LeaveBalanceAlloc(BaseModel):
    employee_id: int
    year: int
    leave_type: LeaveType
    total_allocated: Decimal = Field(..., ge=0)


class LeaveRequestCreate(BaseModel):
    employee_id: Optional[int] = None  # If not provided, inferred from logged-in user
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=3, max_length=500)


class LeaveReview(BaseModel):
    status: LeaveStatus = Field(..., description="Must be APPROVED or REJECTED")
    admin_remarks: Optional[str] = Field(None, max_length=255)


class LeaveRequestResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    leave_type: LeaveType
    start_date: date
    end_date: date
    days: Decimal
    reason: str
    status: LeaveStatus
    reviewed_by: Optional[int] = None
    reviewed_by_username: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    admin_remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
