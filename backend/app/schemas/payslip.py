"""
Payslip Schemas
===============
Pydantic DTOs for payslip API request/response serialisation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PayslipGenerateRequest(BaseModel):
    """
    Optional override parameters when generating a payslip.
    Both fields are normally derived from the payroll record itself,
    but callers may specify a custom company name displayed on the PDF.
    """
    company_name: Optional[str] = "Acme Corporation Pvt. Ltd."
    company_address: Optional[str] = "123 Business Park, Tech City - 560001"
    company_email: Optional[str] = "hr@acmecorp.com"


class PayslipResponse(BaseModel):
    """Full metadata about a generated payslip returned to the client."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    payslip_number: str
    payroll_id: int
    employee_id: int

    # Denormalised convenience fields (populated by the service layer)
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None
    department_name: Optional[str] = None
    designation_title: Optional[str] = None

    month: int
    year: int
    file_path: str
    download_count: int
    generated_at: datetime
    updated_at: datetime
