"""
Payslip Model
=============
Stores metadata for a generated PDF payslip. The actual PDF binary is saved
to disk under ``uploads/payslips/`` and the relative path is persisted here.

Relationship:
  Payroll  1──1  Payslip  (one payslip per finalised payroll record)
  Employee 1──*  Payslip  (an employee accumulates payslips over time)
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, SmallInteger, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db.session import Base


class Payslip(Base):
    __tablename__ = "payslips"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Unique human-readable payslip number e.g. "PS-202611-EMP1001"
    payslip_number = Column(String(60), unique=True, nullable=False, index=True)

    # FK to the parent payroll record (one-to-one)
    payroll_id = Column(
        Integer,
        ForeignKey("payroll.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Denormalised for fast employee self-service queries
    employee_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    month = Column(SmallInteger, nullable=False)   # 1-12
    year = Column(SmallInteger, nullable=False)    # e.g. 2026

    # Relative path from project root: "uploads/payslips/PS-202611-EMP1001.pdf"
    file_path = Column(String(255), nullable=False)

    # How many times the PDF has been downloaded
    download_count = Column(Integer, default=0, nullable=False)

    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        # Composite guard: one payslip document per employee per month/year
        UniqueConstraint("employee_id", "month", "year", name="uq_payslip_emp_month_year"),
    )

    # Relationships
    payroll = relationship("Payroll", back_populates="payslip")
    employee = relationship("Employee", back_populates="payslips")

    def __repr__(self):
        return (
            f"<Payslip {self.payslip_number} emp_id={self.employee_id} "
            f"{self.year}-{self.month:02d}>"
        )
