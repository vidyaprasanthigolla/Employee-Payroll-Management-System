import enum
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, SmallInteger, Date, Numeric, Text,
    DateTime, Enum, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.salary import ComponentType


class PayrollStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"


class PaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"
    CASH = "CASH"


class Payroll(Base):
    __tablename__ = "payroll"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    payroll_batch_code = Column(String(50), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False, index=True)
    month = Column(SmallInteger, nullable=False, index=True)
    year = Column(SmallInteger, nullable=False, index=True)
    payable_days = Column(Numeric(4, 1), default=Decimal("30.0"), nullable=False)
    present_days = Column(Numeric(4, 1), default=Decimal("0.0"), nullable=False)
    paid_leaves = Column(Numeric(4, 1), default=Decimal("0.0"), nullable=False)
    unpaid_leaves = Column(Numeric(4, 1), default=Decimal("0.0"), nullable=False)
    gross_salary = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_deductions = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    lop_deduction = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    net_salary = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status = Column(Enum(PayrollStatus), default=PayrollStatus.DRAFT, nullable=False, index=True)
    processed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    payment_date = Column(Date, nullable=True)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.BANK_TRANSFER, nullable=False)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("employee_id", "month", "year", name="uq_employee_month_year"),
    )

    # Relationships
    employee = relationship("Employee", back_populates="payroll_records")
    processor = relationship("User", foreign_keys=[processed_by])
    approver = relationship("User", foreign_keys=[approved_by])
    details = relationship("PayrollDetail", back_populates="payroll", cascade="all, delete-orphan")
    # One-to-one: each payroll record maps to exactly one generated payslip PDF
    payslip = relationship("Payslip", back_populates="payroll", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Payroll emp_id={self.employee_id} period={self.year}-{self.month:02d} net={self.net_salary} [{self.status}]>"


class PayrollDetail(Base):
    __tablename__ = "payroll_details"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    payroll_id = Column(Integer, ForeignKey("payroll.id", ondelete="CASCADE"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("salary_components.id", ondelete="RESTRICT"), nullable=False)
    component_name = Column(String(100), nullable=False)  # Immutable snapshot
    component_type = Column(Enum(ComponentType), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    payroll = relationship("Payroll", back_populates="details")
    component = relationship("SalaryComponent")

    def __repr__(self):
        return f"<PayrollDetail {self.component_name} ({self.component_type}): {self.amount}>"
