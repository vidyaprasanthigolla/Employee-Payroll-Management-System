from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.models.payroll import PayrollStatus, PaymentMethod
from app.models.salary import ComponentType


class PayrollProcessRequest(BaseModel):
    month: int = Field(..., ge=1, le=12, description="Target payroll month (1-12)")
    year: int = Field(..., ge=2000, description="Target payroll year (e.g. 2026)")
    employee_ids: Optional[List[int]] = Field(None, description="Optional subset of employees; processes all active employees if omitted")
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    remarks: Optional[str] = None


class PayrollStatusUpdate(BaseModel):
    status: PayrollStatus = Field(..., description="Target status (APPROVED, PAID, REJECTED)")
    payment_date: Optional[date] = None
    remarks: Optional[str] = None


class PayrollDetailItem(BaseModel):
    id: int
    component_name: str
    component_type: ComponentType
    amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class PayrollResponse(BaseModel):
    id: int
    payroll_batch_code: str
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: Optional[str] = None
    designation_title: Optional[str] = None
    bank_name: Optional[str] = None
    masked_bank_account: Optional[str] = None
    month: int
    year: int
    payable_days: Decimal
    present_days: Decimal
    paid_leaves: Decimal
    unpaid_leaves: Decimal
    gross_salary: Decimal
    total_deductions: Decimal
    lop_deduction: Decimal
    net_salary: Decimal
    status: PayrollStatus
    processed_by: Optional[int] = None
    processed_by_username: Optional[str] = None
    approved_by: Optional[int] = None
    approved_by_username: Optional[str] = None
    payment_date: Optional[date] = None
    payment_method: PaymentMethod
    remarks: Optional[str] = None
    details: List[PayrollDetailItem] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayrollBatchSummary(BaseModel):
    payroll_batch_code: str
    month: int
    year: int
    total_employees_processed: int
    total_gross_disbursed: Decimal
    total_statutory_deductions: Decimal
    total_lop_deductions: Decimal
    total_net_disbursed: Decimal
    records: List[PayrollResponse]
