import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERN = "INTERN"


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PROBATION = "PROBATION"
    RESIGNED = "RESIGNED"
    TERMINATED = "TERMINATED"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_code = Column(String(20), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    date_of_joining = Column(Date, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    designation_id = Column(Integer, ForeignKey("designations.id", ondelete="SET NULL"), nullable=True, index=True)
    employment_type = Column(Enum(EmploymentType), default=EmploymentType.FULL_TIME, nullable=False)
    bank_name = Column(String(100), nullable=False)
    bank_account_number = Column(String(50), nullable=False)
    ifsc_code = Column(String(20), nullable=False)
    pan_number = Column(String(20), nullable=False)
    status = Column(Enum(EmployeeStatus), default=EmployeeStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="employee_profile")
    department = relationship("Department", back_populates="employees")
    designation = relationship("Designation", back_populates="employees")
    attendance_records = relationship("Attendance", back_populates="employee", cascade="all, delete-orphan")
    leave_balances = relationship("LeaveBalance", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")
    salary_components = relationship("EmployeeSalaryComponent", back_populates="employee", cascade="all, delete-orphan")
    payroll_records = relationship("Payroll", back_populates="employee")
    payslips = relationship("Payslip", back_populates="employee", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def masked_bank_account(self) -> str:
        """Returns account with all but last 4 digits masked with asterisks."""
        if not self.bank_account_number:
            return ""
        clean = str(self.bank_account_number).strip()
        if len(clean) <= 4:
            return clean
        return f"{'*' * (len(clean) - 4)}{clean[-4:]}"

    def __repr__(self):
        return f"<Employee id={self.id} code='{self.employee_code}' name='{self.full_name}'>"
