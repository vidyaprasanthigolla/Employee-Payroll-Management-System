import calendar
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List
from app.schemas.salary import EmployeeSalaryBreakdownResponse
from app.schemas.attendance import MonthlyAttendanceSummary
from app.models.salary import ComponentType


class PayrollCalculator:
    """
    Precision Financial Engine for Monthly Wage Calculations.
    Enforces pure fixed-point decimal arithmetic (ROUND_HALF_UP)
    to eliminate IEEE-754 floating-point rounding errors.
    """

    @staticmethod
    def calculate_employee_payroll(
        employee_id: int,
        month: int,
        year: int,
        salary_breakdown: EmployeeSalaryBreakdownResponse,
        attendance_summary: MonthlyAttendanceSummary
    ) -> Dict[str, Any]:
        calendar_days = calendar.monthrange(year, month)[1]
        payable_days = Decimal(str(calendar_days))

        gross_salary = salary_breakdown.gross_monthly_salary
        total_deductions = salary_breakdown.total_monthly_deductions

        # Loss of Pay (LOP) / Unpaid Leaves
        unpaid_days = Decimal(str(attendance_summary.unpaid_leave_days))
        lop_deduction = Decimal("0.00")

        if unpaid_days > Decimal("0.00") and payable_days > Decimal("0.00") and gross_salary > Decimal("0.00"):
            # Daily Wage Rate Basis = Gross Salary / Payable Days
            daily_rate = (gross_salary / payable_days).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            lop_deduction = (daily_rate * unpaid_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Net Salary = Gross Salary - Total Statutory Deductions - LOP Deduction
        net_salary = gross_salary - total_deductions - lop_deduction
        if net_salary < Decimal("0.00"):
            net_salary = Decimal("0.00")

        # Snapshot details
        details = []
        for e in salary_breakdown.earnings:
            details.append({
                "component_id": e.component_id,
                "component_name": e.component_name,
                "component_type": ComponentType.EARNING,
                "amount": e.amount
            })

        for d in salary_breakdown.deductions:
            details.append({
                "component_id": d.component_id,
                "component_name": d.component_name,
                "component_type": ComponentType.DEDUCTION,
                "amount": d.amount
            })

        return {
            "employee_id": employee_id,
            "month": month,
            "year": year,
            "payable_days": payable_days,
            "present_days": Decimal(str(attendance_summary.effective_present_days)),
            "paid_leaves": Decimal(str(attendance_summary.leave_days)),
            "unpaid_leaves": unpaid_days,
            "gross_salary": gross_salary,
            "total_deductions": total_deductions,
            "lop_deduction": lop_deduction,
            "net_salary": net_salary,
            "details": details
        }
