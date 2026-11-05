import enum
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Boolean, Date, Numeric, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class ComponentType(str, enum.Enum):
    EARNING = "EARNING"
    DEDUCTION = "DEDUCTION"


class CalculationType(str, enum.Enum):
    FLAT = "FLAT"
    PERCENTAGE = "PERCENTAGE"


class SalaryComponent(Base):
    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    code = Column(String(20), unique=True, index=True, nullable=False)
    type = Column(Enum(ComponentType), nullable=False, index=True)
    calculation_type = Column(Enum(CalculationType), default=CalculationType.FLAT, nullable=False)
    is_taxable = Column(Boolean, default=True, nullable=False)
    is_statutory = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee_assignments = relationship("EmployeeSalaryComponent", back_populates="component")

    def __repr__(self):
        return f"<SalaryComponent code='{self.code}' name='{self.name}' type={self.type}>"


class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    base_monthly_salary = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SalaryStructure name='{self.name}' base={self.base_monthly_salary}>"


class EmployeeSalaryComponent(Base):
    __tablename__ = "employee_salary_components"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("salary_components.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    percentage = Column(Numeric(5, 2), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    effective_from = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("employee_id", "component_id", name="uq_emp_salary_component"),
    )

    # Relationships
    employee = relationship("Employee", back_populates="salary_components")
    component = relationship("SalaryComponent", back_populates="employee_assignments")

    def __repr__(self):
        return f"<EmployeeSalaryComponent emp_id={self.employee_id} comp_id={self.component_id} amount={self.amount}>"
