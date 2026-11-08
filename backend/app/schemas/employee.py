from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from app.models.employee import Gender, EmploymentType, EmployeeStatus


class EmployeeBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=7, max_length=20)
    address: Optional[str] = None
    date_of_birth: date
    gender: Gender
    date_of_joining: date
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    bank_name: str = Field(..., min_length=2, max_length=100)
    bank_account_number: str = Field(..., min_length=5, max_length=50)
    ifsc_code: str = Field(..., min_length=4, max_length=20)
    pan_number: str = Field(..., min_length=5, max_length=20)
    status: EmployeeStatus = EmployeeStatus.ACTIVE


class EmployeeCreate(EmployeeBase):
    user_id: Optional[int] = None
    # Optional fields to auto-provision user login account simultaneously
    create_login_account: bool = False
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    date_of_joining: Optional[date] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    employment_type: Optional[EmploymentType] = None
    bank_name: Optional[str] = Field(None, min_length=2, max_length=100)
    bank_account_number: Optional[str] = Field(None, min_length=5, max_length=50)
    ifsc_code: Optional[str] = Field(None, min_length=4, max_length=20)
    pan_number: Optional[str] = Field(None, min_length=5, max_length=20)
    status: Optional[EmployeeStatus] = None

class EmployeeNameUpdate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)


class EmployeeStatusUpdate(BaseModel):
    status: EmployeeStatus


class EmployeeResponse(EmployeeBase):
    id: int
    employee_code: str
    user_id: int
    email: Optional[str] = None
    full_name: str
    masked_bank_account: str
    department_name: Optional[str] = None
    designation_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeePaginationResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[EmployeeResponse]
