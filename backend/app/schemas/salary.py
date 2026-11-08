from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from app.models.salary import ComponentType, CalculationType


class SalaryComponentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    code: str = Field(..., min_length=2, max_length=20)
    type: ComponentType
    calculation_type: CalculationType = CalculationType.FLAT
    default_value: Decimal = Field(default=Decimal("0.00"), ge=0)
    is_taxable: bool = True
    is_statutory: bool = False
    is_active: bool = True
    description: Optional[str] = None


class SalaryComponentCreate(SalaryComponentBase):
    pass


class SalaryComponentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    type: Optional[ComponentType] = None
    calculation_type: Optional[CalculationType] = None
    default_value: Optional[Decimal] = Field(None, ge=0)
    is_taxable: Optional[bool] = None
    is_statutory: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class SalaryComponentResponse(SalaryComponentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalaryStructureBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    base_monthly_salary: Decimal = Field(..., ge=0)
    is_active: bool = True


class SalaryStructureCreate(SalaryStructureBase):
    pass


class SalaryStructureUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    base_monthly_salary: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class SalaryStructureResponse(SalaryStructureBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComponentAssignmentItem(BaseModel):
    component_id: int
    amount: Decimal = Field(Decimal("0.00"), ge=0)
    percentage: Optional[Decimal] = Field(None, ge=0, le=100)


class AssignSalaryStructureRequest(BaseModel):
    effective_from: Optional[date] = None
    components: List[ComponentAssignmentItem]


class EmployeeSalaryComponentResponse(BaseModel):
    id: int
    component_id: int
    component_name: str
    component_code: str
    component_type: ComponentType
    calculation_type: CalculationType
    amount: Decimal
    percentage: Optional[Decimal] = None
    is_statutory: bool
    is_taxable: bool
    effective_from: date

    model_config = ConfigDict(from_attributes=True)


class EmployeeSalaryBreakdownResponse(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    effective_from: date
    gross_monthly_salary: Decimal
    total_monthly_deductions: Decimal
    net_monthly_salary: Decimal
    earnings: List[EmployeeSalaryComponentResponse]
    deductions: List[EmployeeSalaryComponentResponse]
