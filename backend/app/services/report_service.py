"""
Reports Service
===============
Generates management and compliance reports in Excel (.xlsx) and PDF formats:
  1. Monthly Payroll Summary (Excel & PDF)
  2. Department-wise Payroll Breakdown (Excel)
  3. Attendance & Leave Utilization Report (Excel)
  4. Statutory Tax & Deductions Compliance Report (PF, ESI, PT, TDS) (Excel)
"""

import io
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import pandas as pd

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from app.models.payroll import Payroll, PayrollDetail, PayrollStatus
from app.models.employee import Employee
from app.models.department import Department
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest, LeaveBalance


class ReportService:

    @staticmethod
    def generate_monthly_payroll_excel(
        db: Session,
        month: int,
        year: int
    ) -> io.BytesIO:
        """Exports full payroll register for a given month to Excel."""
        records = db.query(Payroll).filter(
            Payroll.month == month,
            Payroll.year == year
        ).all()

        data = []
        for r in records:
            emp: Employee = r.employee
            dept_name = emp.department.name if emp and emp.department else "Unassigned"
            desig_title = emp.designation.title if emp and emp.designation else "Unassigned"

            data.append({
                "Batch Code": r.payroll_batch_code,
                "Employee Code": emp.employee_code if emp else "",
                "Full Name": emp.full_name if emp else "",
                "Department": dept_name,
                "Designation": desig_title,
                "Month/Year": f"{r.month:02d}/{r.year}",
                "Payable Days": float(r.payable_days),
                "Present Days": float(r.present_days),
                "Unpaid LOP Days": float(r.unpaid_leaves),
                "Gross Salary (INR)": float(r.gross_salary),
                "Total Deductions (INR)": float(r.total_deductions),
                "LOP Deduction (INR)": float(r.lop_deduction),
                "Net Salary (INR)": float(r.net_salary),
                "Status": r.status.value,
                "Payment Method": r.payment_method.value,
                "Payment Date": str(r.payment_date) if r.payment_date else "Pending"
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=f"Payroll_{year}_{month:02d}")
        output.seek(0)
        return output

    @staticmethod
    def generate_monthly_payroll_pdf(
        db: Session,
        month: int,
        year: int,
        company_name: str = "Acme Corporation Pvt. Ltd."
    ) -> io.BytesIO:
        """Generates a landscape summary PDF of the monthly payroll batch."""
        records = db.query(Payroll).filter(
            Payroll.month == month,
            Payroll.year == year
        ).all()

        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            topMargin=1 * cm,
            bottomMargin=1 * cm,
            leftMargin=1 * cm,
            rightMargin=1 * cm
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Normal"],
            fontSize=16,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1a2f5a"),
            alignment=TA_CENTER,
            spaceAfter=6
        )
        sub_style = ParagraphStyle(
            "ReportSub",
            parent=styles["Normal"],
            fontSize=10,
            fontName="Helvetica",
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        cell_style = ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontSize=8,
            fontName="Helvetica"
        )
        hdr_style = ParagraphStyle(
            "Hdr",
            parent=styles["Normal"],
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=colors.white
        )

        story = [
            Paragraph(f"{company_name} - Monthly Payroll Summary", title_style),
            Paragraph(f"Pay Period: {month:02d}/{year} | Total Records: {len(records)}", sub_style),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2e6fad")),
            Spacer(1, 0.4 * cm)
        ]

        table_data = [[
            Paragraph("Batch", hdr_style),
            Paragraph("Emp Code", hdr_style),
            Paragraph("Name", hdr_style),
            Paragraph("Department", hdr_style),
            Paragraph("Gross (₹)", hdr_style),
            Paragraph("Deductions (₹)", hdr_style),
            Paragraph("LOP (₹)", hdr_style),
            Paragraph("Net (₹)", hdr_style),
            Paragraph("Status", hdr_style)
        ]]

        total_gross = Decimal("0.00")
        total_net = Decimal("0.00")

        for r in records:
            emp: Employee = r.employee
            table_data.append([
                Paragraph(r.payroll_batch_code, cell_style),
                Paragraph(emp.employee_code if emp else "", cell_style),
                Paragraph(emp.full_name if emp else "", cell_style),
                Paragraph(emp.department.name if emp and emp.department else "—", cell_style),
                Paragraph(f"{r.gross_salary:,.2f}", cell_style),
                Paragraph(f"{r.total_deductions:,.2f}", cell_style),
                Paragraph(f"{r.lop_deduction:,.2f}", cell_style),
                Paragraph(f"{r.net_salary:,.2f}", cell_style),
                Paragraph(r.status.value, cell_style)
            ])
            total_gross += r.gross_salary
            total_net += r.net_salary

        # Grand Total Row
        bold_cell = ParagraphStyle("BoldCell", parent=cell_style, fontName="Helvetica-Bold")
        table_data.append([
            Paragraph("TOTAL", bold_cell),
            Paragraph("", cell_style),
            Paragraph("", cell_style),
            Paragraph("", cell_style),
            Paragraph(f"{total_gross:,.2f}", bold_cell),
            Paragraph("", cell_style),
            Paragraph("", cell_style),
            Paragraph(f"{total_net:,.2f}", bold_cell),
            Paragraph("", cell_style)
        ])

        col_w = (landscape(A4)[0] - 2 * cm) / 9
        report_table = Table(table_data, colWidths=[col_w] * 9)
        report_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2f5a")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9"))
        ]))

        story.append(report_table)
        doc.build(story)
        output.seek(0)
        return output

    @staticmethod
    def generate_department_payroll_excel(
        db: Session,
        month: int,
        year: int
    ) -> io.BytesIO:
        """Generates departmental cost breakdown report in Excel."""
        depts = db.query(Department).all()
        data = []

        for d in depts:
            records = db.query(Payroll).join(Employee).filter(
                Employee.department_id == d.id,
                Payroll.month == month,
                Payroll.year == year
            ).all()

            headcount = len(records)
            gross = sum([r.gross_salary for r in records], Decimal("0.00"))
            deductions = sum([r.total_deductions for r in records], Decimal("0.00"))
            net = sum([r.net_salary for r in records], Decimal("0.00"))

            data.append({
                "Department": d.name,
                "Employee Count": headcount,
                "Total Gross Cost (INR)": float(gross),
                "Total Deductions (INR)": float(deductions),
                "Total Net Disbursed (INR)": float(net)
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Department_Breakdown")
        output.seek(0)
        return output

    @staticmethod
    def generate_statutory_deductions_excel(
        db: Session,
        month: int,
        year: int
    ) -> io.BytesIO:
        """Generates statutory deductions compliance report (PF, ESI, PT, TDS)."""
        records = db.query(Payroll).filter(
            Payroll.month == month,
            Payroll.year == year
        ).all()

        data = []
        for r in records:
            emp: Employee = r.employee
            comp_map = {d.component_name: d.amount for d in r.details}

            data.append({
                "Employee Code": emp.employee_code if emp else "",
                "Full Name": emp.full_name if emp else "",
                "PAN Number": emp.pan_number if emp else "",
                "Provident Fund (PF)": float(comp_map.get("Provident Fund", 0.00)),
                "Employee State Insurance (ESI)": float(comp_map.get("Employee State Insurance", 0.00)),
                "Professional Tax (PT)": float(comp_map.get("Professional Tax", 0.00)),
                "Tax Deducted at Source (TDS)": float(comp_map.get("Tax Deducted at Source", 0.00)),
                "Total Statutory Deductions": float(r.total_deductions)
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Statutory_Compliance")
        output.seek(0)
        return output
