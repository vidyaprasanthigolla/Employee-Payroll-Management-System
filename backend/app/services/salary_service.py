from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.salary import (
    SalaryComponent,
    SalaryStructure,
    EmployeeSalaryComponent,
    ComponentType,
    CalculationType
)
from app.models.employee import Employee
from app.schemas.salary import (
    SalaryComponentCreate,
    SalaryComponentUpdate,
    SalaryStructureCreate,
    SalaryStructureUpdate,
    AssignSalaryStructureRequest,
    EmployeeSalaryComponentResponse,
    EmployeeSalaryBreakdownResponse
)
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException, PayrollException


class SalaryService:
    @staticmethod
    def get_components(
        db: Session,
        comp_type: Optional[ComponentType] = None,
        is_active: Optional[bool] = None
    ) -> List[SalaryComponent]:
        query = db.query(SalaryComponent)
        if comp_type:
            query = query.filter(SalaryComponent.type == comp_type)
        if is_active is not None:
            query = query.filter(SalaryComponent.is_active == is_active)
        return query.order_by(SalaryComponent.type.asc(), SalaryComponent.name.asc()).all()

    @staticmethod
    def get_component_by_id(db: Session, comp_id: int) -> SalaryComponent:
        comp = db.query(SalaryComponent).filter(SalaryComponent.id == comp_id).first()
        if not comp:
            raise ResourceNotFoundException("Salary Component", comp_id)
        return comp

    @staticmethod
    def create_component(db: Session, comp_in: SalaryComponentCreate) -> SalaryComponent:
        clean_code = comp_in.code.strip().upper()
        clean_name = comp_in.name.strip()

        existing = db.query(SalaryComponent).filter(
            (func.lower(SalaryComponent.code) == clean_code.lower()) |
            (func.lower(SalaryComponent.name) == clean_name.lower())
        ).first()

        if existing:
            if existing.code.upper() == clean_code:
                raise DuplicateResourceException(f"Salary Component with code '{clean_code}' already exists.")
            raise DuplicateResourceException(f"Salary Component with name '{clean_name}' already exists.")

        comp = SalaryComponent(
            name=clean_name,
            code=clean_code,
            type=comp_in.type,
            calculation_type=comp_in.calculation_type,
            is_taxable=comp_in.is_taxable,
            is_statutory=comp_in.is_statutory,
            is_active=comp_in.is_active,
            description=comp_in.description.strip() if comp_in.description else None
        )
        db.add(comp)
        db.commit()
        db.refresh(comp)
        return comp

    @staticmethod
    def update_component(db: Session, comp_id: int, comp_in: SalaryComponentUpdate) -> SalaryComponent:
        comp = SalaryService.get_component_by_id(db, comp_id)

        if comp_in.code:
            clean_code = comp_in.code.strip().upper()
            existing = db.query(SalaryComponent).filter(
                func.lower(SalaryComponent.code) == clean_code.lower(),
                SalaryComponent.id != comp_id
            ).first()
            if existing:
                raise DuplicateResourceException(f"Component code '{clean_code}' is already used.")
            comp.code = clean_code

        if comp_in.name:
            clean_name = comp_in.name.strip()
            existing = db.query(SalaryComponent).filter(
                func.lower(SalaryComponent.name) == clean_name.lower(),
                SalaryComponent.id != comp_id
            ).first()
            if existing:
                raise DuplicateResourceException(f"Component name '{clean_name}' is already used.")
            comp.name = clean_name

        for field in ["type", "calculation_type", "is_taxable", "is_statutory", "is_active", "description"]:
            val = getattr(comp_in, field)
            if val is not None:
                setattr(comp, field, val)

        db.commit()
        db.refresh(comp)
        return comp

    @staticmethod
    def delete_component(db: Session, comp_id: int) -> bool:
        comp = SalaryService.get_component_by_id(db, comp_id)
        # Verify no active employee assignments
        assigned = db.query(EmployeeSalaryComponent).filter(EmployeeSalaryComponent.component_id == comp_id).count()
        if assigned > 0:
            raise PayrollException(
                f"Cannot delete component '{comp.name}' because {assigned} employee salary structures currently reference it.",
                status_code=400
            )
        db.delete(comp)
        db.commit()
        return True

    @staticmethod
    def get_structures(db: Session, is_active: Optional[bool] = None) -> List[SalaryStructure]:
        query = db.query(SalaryStructure)
        if is_active is not None:
            query = query.filter(SalaryStructure.is_active == is_active)
        return query.order_by(SalaryStructure.name.asc()).all()

    @staticmethod
    def create_structure(db: Session, struct_in: SalaryStructureCreate) -> SalaryStructure:
        existing = db.query(SalaryStructure).filter(
            func.lower(SalaryStructure.name) == struct_in.name.strip().lower()
        ).first()
        if existing:
            raise DuplicateResourceException(f"Salary structure template '{struct_in.name}' already exists.")

        struct = SalaryStructure(
            name=struct_in.name.strip(),
            description=struct_in.description.strip() if struct_in.description else None,
            base_monthly_salary=struct_in.base_monthly_salary,
            is_active=struct_in.is_active
        )
        db.add(struct)
        db.commit()
        db.refresh(struct)
        return struct

    @staticmethod
    def assign_salary_structure(
        db: Session,
        employee_id: int,
        assign_in: AssignSalaryStructureRequest
    ) -> EmployeeSalaryBreakdownResponse:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            raise ResourceNotFoundException("Employee", employee_id)

        effective_date = assign_in.effective_from or emp.date_of_joining

        # Load all requested components
        comp_items = assign_in.components
        comp_ids = [item.component_id for item in comp_items]
        components = db.query(SalaryComponent).filter(SalaryComponent.id.in_(comp_ids)).all()
        comp_dict = {c.id: c for c in components}

        # Identify Basic component for percentage-based evaluations
        basic_amount = Decimal("0.00")
        for item in comp_items:
            comp = comp_dict.get(item.component_id)
            if comp and comp.code == "BASIC":
                basic_amount = Decimal(str(item.amount))
                break

        # Remove previous assignments for clean update
        db.query(EmployeeSalaryComponent).filter(EmployeeSalaryComponent.employee_id == employee_id).delete()

        for item in comp_items:
            comp = comp_dict.get(item.component_id)
            if not comp:
                continue

            final_amount = Decimal(str(item.amount))
            # Calculate percentage-based amounts (e.g. 12% of basic)
            if comp.calculation_type == CalculationType.PERCENTAGE and item.percentage is not None and basic_amount > Decimal("0.00"):
                pct = Decimal(str(item.percentage))
                final_amount = ((basic_amount * pct) / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            esc = EmployeeSalaryComponent(
                employee_id=employee_id,
                component_id=comp.id,
                amount=final_amount,
                percentage=item.percentage,
                is_active=True,
                effective_from=effective_date
            )
            db.add(esc)

        db.commit()
        return SalaryService.get_employee_salary_breakdown(db, employee_id)

    @staticmethod
    def get_employee_salary_breakdown(db: Session, employee_id: int) -> EmployeeSalaryBreakdownResponse:
        emp = db.query(Employee).filter(Employee.id == employee_id).first()
        if not emp:
            raise ResourceNotFoundException("Employee", employee_id)

        assignments = db.query(EmployeeSalaryComponent).join(
            SalaryComponent, EmployeeSalaryComponent.component_id == SalaryComponent.id
        ).filter(
            EmployeeSalaryComponent.employee_id == employee_id,
            EmployeeSalaryComponent.is_active == True
        ).all()

        earnings: List[EmployeeSalaryComponentResponse] = []
        deductions: List[EmployeeSalaryComponentResponse] = []
        gross = Decimal("0.00")
        total_ded = Decimal("0.00")
        effective_from = emp.date_of_joining

        for a in assignments:
            comp = a.component
            effective_from = a.effective_from
            resp_item = EmployeeSalaryComponentResponse(
                id=a.id,
                component_id=comp.id,
                component_name=comp.name,
                component_code=comp.code,
                component_type=comp.type,
                calculation_type=comp.calculation_type,
                amount=a.amount,
                percentage=a.percentage,
                is_statutory=comp.is_statutory,
                is_taxable=comp.is_taxable,
                effective_from=a.effective_from
            )
            if comp.type == ComponentType.EARNING:
                earnings.append(resp_item)
                gross += a.amount
            else:
                deductions.append(resp_item)
                total_ded += a.amount

        net = gross - total_ded

        return EmployeeSalaryBreakdownResponse(
            employee_id=emp.id,
            employee_code=emp.employee_code,
            employee_name=emp.full_name,
            effective_from=effective_from,
            gross_monthly_salary=gross,
            total_monthly_deductions=total_ded,
            net_monthly_salary=net,
            earnings=earnings,
            deductions=deductions
        )

    @staticmethod
    def seed_default_components(db: Session) -> List[SalaryComponent]:
        defaults = [
            # Earnings
            {"name": "Basic Salary", "code": "BASIC", "type": ComponentType.EARNING, "calc": CalculationType.FLAT, "taxable": True, "statutory": True, "desc": "Fixed core wage component"},
            {"name": "House Rent Allowance", "code": "HRA", "type": ComponentType.EARNING, "calc": CalculationType.PERCENTAGE, "taxable": True, "statutory": False, "desc": "Housing subsidy (e.g. 40% of Basic)"},
            {"name": "Dearness Allowance", "code": "DA", "type": ComponentType.EARNING, "calc": CalculationType.PERCENTAGE, "taxable": True, "statutory": False, "desc": "Cost of living adjustment"},
            {"name": "Conveyance Allowance", "code": "CONV", "type": ComponentType.EARNING, "calc": CalculationType.FLAT, "taxable": False, "statutory": False, "desc": "Commute and transit allowance"},
            {"name": "Medical Allowance", "code": "MED", "type": ComponentType.EARNING, "calc": CalculationType.FLAT, "taxable": False, "statutory": False, "desc": "Routine health and wellness reimbursement"},
            {"name": "Special Allowance", "code": "SPL_ALW", "type": ComponentType.EARNING, "calc": CalculationType.FLAT, "taxable": True, "statutory": False, "desc": "Performance and executive allowance"},
            {"name": "Performance Bonus", "code": "BONUS", "type": ComponentType.EARNING, "calc": CalculationType.FLAT, "taxable": True, "statutory": False, "desc": "Quarterly or discretionary milestone incentive"},
            # Deductions
            {"name": "Provident Fund", "code": "PF", "type": ComponentType.DEDUCTION, "calc": CalculationType.PERCENTAGE, "taxable": False, "statutory": True, "desc": "Employee statutory retirement pension (12% of Basic)"},
            {"name": "Employee State Insurance", "code": "ESI", "type": ComponentType.DEDUCTION, "calc": CalculationType.PERCENTAGE, "taxable": False, "statutory": True, "desc": "State healthcare safety contribution"},
            {"name": "Professional Tax", "code": "PT", "type": ComponentType.DEDUCTION, "calc": CalculationType.FLAT, "taxable": False, "statutory": True, "desc": "State statutory professional levy"},
            {"name": "Tax Deducted at Source", "code": "TDS", "type": ComponentType.DEDUCTION, "calc": CalculationType.FLAT, "taxable": False, "statutory": True, "desc": "Federal/National income tax withholding"},
        ]

        created = []
        for d in defaults:
            existing = db.query(SalaryComponent).filter(SalaryComponent.code == d["code"]).first()
            if not existing:
                comp = SalaryComponent(
                    name=d["name"],
                    code=d["code"],
                    type=d["type"],
                    calculation_type=d["calc"],
                    is_taxable=d["taxable"],
                    is_statutory=d["statutory"],
                    is_active=True,
                    description=d["desc"]
                )
                db.add(comp)
                created.append(comp)
            else:
                created.append(existing)

        db.commit()
        return created
