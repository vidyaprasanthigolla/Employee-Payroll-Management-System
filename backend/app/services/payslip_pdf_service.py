"""
Payslip PDF Service
===================
Generates a professional, print-ready payslip PDF using ReportLab.

PDF layout (top → bottom):
  ┌─────────────────────────────────────────────────┐
  │  Company header (name, address, logo placeholder)│
  │  ─────────────────── PAYSLIP ──────────────────  │
  │  Employee details table (left) | Period (right)  │
  │  ─────────────────────────────────────────────── │
  │  Earnings table         | Deductions table        │
  │  ─────────────────────────────────────────────── │
  │  Gross Salary           | Total Deductions        │
  │  LOP Deduction          | Net Salary              │
  │  ─────────────────────────────────────────────── │
  │  Amount in Words                                  │
  │  Disclaimer / authorised signatory               │
  └─────────────────────────────────────────────────┘
"""

import os
import calendar
from decimal import Decimal
from typing import Dict, List, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
BRAND_DARK   = colors.HexColor("#1a2f5a")   # Dark navy header background
BRAND_ACCENT = colors.HexColor("#2e6fad")   # Accent blue
EARN_BG      = colors.HexColor("#e8f4f8")   # Light blue for earnings rows
DED_BG       = colors.HexColor("#fce8e8")   # Light red for deduction rows
HEADER_TEXT  = colors.white
TABLE_GRID   = colors.HexColor("#cccccc")
NET_BG       = colors.HexColor("#d4edda")   # Green tint for net salary row
LOP_BG       = colors.HexColor("#fff3cd")   # Amber tint for LOP row


# ---------------------------------------------------------------------------
# Amount-in-words helper
# ---------------------------------------------------------------------------
_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
    "Sixteen", "Seventeen", "Eighteen", "Nineteen"
]
_TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty",
    "Sixty", "Seventy", "Eighty", "Ninety"
]


def _chunk_to_words(n: int) -> str:
    """Convert an integer 0–999 to English words."""
    if n == 0:
        return ""
    elif n < 20:
        return _ONES[n]
    elif n < 100:
        rest = _TENS[n // 10]
        if n % 10:
            rest += " " + _ONES[n % 10]
        return rest
    else:
        rest = _ONES[n // 100] + " Hundred"
        if n % 100:
            rest += " " + _chunk_to_words(n % 100)
        return rest


def amount_in_words(amount: Decimal) -> str:
    """
    Convert a Decimal monetary amount to its English words representation.
    Example: Decimal("7150.50") → "Seven Thousand One Hundred Fifty and 50/100 Only"
    """
    amount = amount.quantize(Decimal("0.01"))
    rupees = int(amount)
    paise  = int((amount - rupees) * 100)

    if rupees == 0:
        words = "Zero"
    else:
        parts = []
        crores    = rupees // 10_000_000
        rupees   %= 10_000_000
        lakhs     = rupees // 100_000
        rupees   %= 100_000
        thousands = rupees // 1_000
        rupees   %= 1_000
        hundreds  = rupees

        if crores:
            parts.append(_chunk_to_words(crores) + " Crore")
        if lakhs:
            parts.append(_chunk_to_words(lakhs) + " Lakh")
        if thousands:
            parts.append(_chunk_to_words(thousands) + " Thousand")
        if hundreds:
            parts.append(_chunk_to_words(hundreds))
        words = " ".join(parts)

    if paise:
        return f"{words} and {paise:02d}/100 Only"
    return f"{words} Only"


# ---------------------------------------------------------------------------
# Main PDF generator
# ---------------------------------------------------------------------------

def generate_payslip_pdf(
    payroll_data: Dict[str, Any],
    output_path: str,
    company_name: str = "Acme Corporation Pvt. Ltd.",
    company_address: str = "123 Business Park, Tech City - 560001",
    company_email: str = "hr@acmecorp.com",
) -> str:
    """
    Build and save a payslip PDF to ``output_path``.

    Parameters
    ----------
    payroll_data : dict
        Keys expected (all strings/Decimals/dates as appropriate):
          employee_code, employee_name, department_name, designation_title,
          date_of_joining, bank_name, masked_bank_account,
          month, year, payment_date,
          payable_days, present_days, paid_leaves, unpaid_leaves,
          gross_salary, total_deductions, lop_deduction, net_salary,
          details: List[{"component_name", "component_type", "amount"}]
    output_path : str
        Absolute filesystem path where the PDF will be written.
    company_name, company_address, company_email : str
        Company branding displayed in the header.

    Returns
    -------
    str
        The ``output_path`` that was written (for convenience).
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # --- Styles ---
    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    style_center = ParagraphStyle("Center", parent=style_normal, alignment=TA_CENTER)
    style_right  = ParagraphStyle("Right",  parent=style_normal, alignment=TA_RIGHT)

    style_company = ParagraphStyle(
        "Company", parent=style_normal,
        fontSize=18, fontName="Helvetica-Bold",
        textColor=HEADER_TEXT, alignment=TA_CENTER, spaceAfter=4
    )
    style_company_sub = ParagraphStyle(
        "CompanySub", parent=style_normal,
        fontSize=9, fontName="Helvetica",
        textColor=HEADER_TEXT, alignment=TA_CENTER
    )
    style_payslip_title = ParagraphStyle(
        "PayslipTitle", parent=style_normal,
        fontSize=13, fontName="Helvetica-Bold",
        textColor=BRAND_DARK, alignment=TA_CENTER, spaceAfter=6, spaceBefore=6
    )
    style_field_label = ParagraphStyle(
        "FieldLabel", parent=style_normal,
        fontSize=8.5, fontName="Helvetica-Bold", textColor=BRAND_DARK
    )
    style_field_value = ParagraphStyle(
        "FieldValue", parent=style_normal,
        fontSize=8.5, fontName="Helvetica"
    )
    style_amount_words = ParagraphStyle(
        "AmountWords", parent=style_normal,
        fontSize=9, fontName="Helvetica-Bold", textColor=BRAND_DARK,
        alignment=TA_LEFT, spaceBefore=4
    )
    style_disclaimer = ParagraphStyle(
        "Disclaimer", parent=style_normal,
        fontSize=7.5, fontName="Helvetica", textColor=colors.grey,
        alignment=TA_CENTER, spaceBefore=8
    )

    # --- Document setup ---
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )

    page_w = A4[0] - 3 * cm   # usable width
    story: List = []

    # =========================================================================
    # 1. Company header banner
    # =========================================================================
    header_data = [[
        Paragraph(company_name, style_company),
    ], [
        Paragraph(company_address, style_company_sub),
    ], [
        Paragraph(f"Email: {company_email}", style_company_sub),
    ]]
    header_table = Table(header_data, colWidths=[page_w])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("TOPPADDING",    (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)

    # =========================================================================
    # 2. Title row: "PAYSLIP FOR <MONTH YEAR>"
    # =========================================================================
    month_name = calendar.month_name[payroll_data["month"]]
    story.append(Paragraph(
        f"PAYSLIP FOR {month_name.upper()} {payroll_data['year']}",
        style_payslip_title
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT))
    story.append(Spacer(1, 0.3 * cm))

    # =========================================================================
    # 3. Employee information grid (two-column)
    # =========================================================================
    def lbl(text):
        return Paragraph(text, style_field_label)

    def val(text):
        return Paragraph(str(text) if text is not None else "—", style_field_value)

    doj = payroll_data.get("date_of_joining")
    doj_str = doj.strftime("%d %b %Y") if doj else "—"

    pay_date = payroll_data.get("payment_date")
    pay_date_str = pay_date.strftime("%d %b %Y") if pay_date else "—"

    masked_acct = payroll_data.get("masked_bank_account") or "XXXXXXXX"

    emp_info = [
        [lbl("Employee Code"),   val(payroll_data["employee_code"]),
         lbl("Employee Name"),   val(payroll_data["employee_name"])],
        [lbl("Department"),      val(payroll_data.get("department_name", "—")),
         lbl("Designation"),     val(payroll_data.get("designation_title", "—"))],
        [lbl("Date of Joining"), val(doj_str),
         lbl("Payment Date"),    val(pay_date_str)],
        [lbl("Bank Name"),       val(payroll_data.get("bank_name", "—")),
         lbl("Bank Account"),    val(masked_acct)],
        [lbl("Payable Days"),    val(str(payroll_data["payable_days"])),
         lbl("Present Days"),    val(str(payroll_data["present_days"]))],
        [lbl("Paid Leaves"),     val(str(payroll_data["paid_leaves"])),
         lbl("Unpaid Leaves"),   val(str(payroll_data["unpaid_leaves"]))],
    ]

    col_w = page_w / 4
    emp_table = Table(emp_info, colWidths=[col_w, col_w, col_w, col_w])
    emp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_GRID),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_GRID),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 0.4 * cm))

    # =========================================================================
    # 4. Earnings & Deductions tables (side-by-side)
    # =========================================================================
    details: List[Dict] = payroll_data.get("details", [])
    earnings    = [d for d in details if d["component_type"] == "EARNING"]
    deductions  = [d for d in details if d["component_type"] == "DEDUCTION"]

    def _currency(amount) -> str:
        return f"₹ {Decimal(str(amount)):,.2f}"

    # Build rows for each table
    earn_rows = [[
        Paragraph("EARNINGS", ParagraphStyle(
            "EarnHdr", parent=style_normal,
            fontSize=9, fontName="Helvetica-Bold", textColor=HEADER_TEXT
        )),
        Paragraph("AMOUNT", ParagraphStyle(
            "EarnHdrR", parent=style_normal,
            fontSize=9, fontName="Helvetica-Bold",
            textColor=HEADER_TEXT, alignment=TA_RIGHT
        )),
    ]]
    for item in earnings:
        earn_rows.append([
            Paragraph(item["component_name"], style_field_value),
            Paragraph(_currency(item["amount"]), ParagraphStyle(
                "AmtRight", parent=style_field_value, alignment=TA_RIGHT
            )),
        ])

    ded_rows = [[
        Paragraph("DEDUCTIONS", ParagraphStyle(
            "DedHdr", parent=style_normal,
            fontSize=9, fontName="Helvetica-Bold", textColor=HEADER_TEXT
        )),
        Paragraph("AMOUNT", ParagraphStyle(
            "DedHdrR", parent=style_normal,
            fontSize=9, fontName="Helvetica-Bold",
            textColor=HEADER_TEXT, alignment=TA_RIGHT
        )),
    ]]
    for item in deductions:
        ded_rows.append([
            Paragraph(item["component_name"], style_field_value),
            Paragraph(_currency(item["amount"]), ParagraphStyle(
                "AmtRight", parent=style_field_value, alignment=TA_RIGHT
            )),
        ])

    # Pad shorter list so both tables have same row count
    max_rows = max(len(earn_rows), len(ded_rows))
    while len(earn_rows) < max_rows:
        earn_rows.append(["", ""])
    while len(ded_rows) < max_rows:
        ded_rows.append(["", ""])

    half_w = page_w / 2 - 0.2 * cm

    earn_table = Table(earn_rows, colWidths=[half_w * 0.65, half_w * 0.35])
    earn_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_ACCENT),  # header row
        ("BACKGROUND", (0, 1), (-1, -1), EARN_BG),
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_GRID),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_GRID),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))

    ded_table = Table(ded_rows, colWidths=[half_w * 0.65, half_w * 0.35])
    ded_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c0392b")),  # header row
        ("TEXTCOLOR",  (0, 0), (-1, 0), HEADER_TEXT),
        ("BACKGROUND", (0, 1), (-1, -1), DED_BG),
        ("BOX",        (0, 0), (-1, -1), 0.5, TABLE_GRID),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, TABLE_GRID),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))

    # Place side-by-side inside a wrapper table
    side_table = Table(
        [[earn_table, "", ded_table]],
        colWidths=[half_w, 0.4 * cm, half_w]
    )
    side_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(side_table)
    story.append(Spacer(1, 0.4 * cm))

    # =========================================================================
    # 5. Summary rows: Gross / Deductions / LOP / Net
    # =========================================================================
    gross    = Decimal(str(payroll_data["gross_salary"]))
    total_d  = Decimal(str(payroll_data["total_deductions"]))
    lop_d    = Decimal(str(payroll_data["lop_deduction"]))
    net      = Decimal(str(payroll_data["net_salary"]))

    def summary_row(label: str, amount: Decimal, bg: colors.Color):
        lbl_para = Paragraph(label, ParagraphStyle(
            "SumLbl", parent=style_normal,
            fontSize=9.5, fontName="Helvetica-Bold", textColor=BRAND_DARK
        ))
        amt_para = Paragraph(_currency(amount), ParagraphStyle(
            "SumAmt", parent=style_normal,
            fontSize=9.5, fontName="Helvetica-Bold",
            textColor=BRAND_DARK, alignment=TA_RIGHT
        ))
        t = Table([[lbl_para, amt_para]], colWidths=[page_w * 0.6, page_w * 0.4])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("BOX",           (0, 0), (-1, -1), 0.5, TABLE_GRID),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ]))
        return t

    story.append(summary_row("Gross Salary", gross, colors.HexColor("#e9ecef")))
    story.append(Spacer(1, 0.1 * cm))
    story.append(summary_row("Total Statutory Deductions", total_d, colors.HexColor("#ffe0e0")))
    if lop_d > Decimal("0.00"):
        story.append(Spacer(1, 0.1 * cm))
        story.append(summary_row(
            f"LOP Deduction ({payroll_data['unpaid_leaves']} unpaid days)", lop_d, LOP_BG
        ))
    story.append(Spacer(1, 0.15 * cm))
    story.append(summary_row("NET SALARY (Take-Home)", net, NET_BG))
    story.append(Spacer(1, 0.4 * cm))

    # =========================================================================
    # 6. Amount in words
    # =========================================================================
    story.append(HRFlowable(width="100%", thickness=0.8, color=TABLE_GRID))
    story.append(Paragraph(
        f"<b>Net Salary in Words:</b> {amount_in_words(net)}",
        style_amount_words
    ))
    story.append(Spacer(1, 0.6 * cm))

    # =========================================================================
    # 7. Disclaimer & Authorised Signatory
    # =========================================================================
    story.append(HRFlowable(width="100%", thickness=0.8, color=TABLE_GRID))
    story.append(Spacer(1, 0.3 * cm))

    sign_data = [[
        Paragraph(
            "This is a system-generated payslip and does not require a physical signature.",
            style_disclaimer
        ),
        Paragraph(
            "<b>Authorised Signatory</b><br/>HR &amp; Payroll Department",
            ParagraphStyle(
                "Sign", parent=style_normal,
                fontSize=8, fontName="Helvetica-Bold",
                alignment=TA_RIGHT
            )
        ),
    ]]
    sign_table = Table(sign_data, colWidths=[page_w * 0.6, page_w * 0.4])
    sign_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(sign_table)

    # --- Build PDF ---
    doc.build(story)
    return output_path
