from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.department import Department
from app.models.designation import Designation
from app.models.employee import Employee
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.schemas.designation import DesignationCreate, DesignationUpdate
from app.core.exceptions import ResourceNotFoundException, DuplicateResourceException, PayrollException


class DepartmentService:
    @staticmethod
    def get_all_departments(db: Session) -> List[Department]:
        return db.query(Department).order_by(Department.name.asc()).all()

    @staticmethod
    def get_department_by_id(db: Session, dept_id: int) -> Department:
        dept = db.query(Department).filter(Department.id == dept_id).first()
        if not dept:
            raise ResourceNotFoundException("Department", dept_id)
        return dept

    @staticmethod
    def create_department(db: Session, dept_in: DepartmentCreate) -> Department:
        existing = db.query(Department).filter(
            func.lower(Department.name) == dept_in.name.strip().lower()
        ).first()
        if existing:
            raise DuplicateResourceException(f"Department '{dept_in.name}' already exists.")

        dept = Department(
            name=dept_in.name.strip(),
            description=dept_in.description.strip() if dept_in.description else None
        )
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return dept

    @staticmethod
    def update_department(db: Session, dept_id: int, dept_in: DepartmentUpdate) -> Department:
        dept = DepartmentService.get_department_by_id(db, dept_id)
        if dept_in.name:
            existing = db.query(Department).filter(
                func.lower(Department.name) == dept_in.name.strip().lower(),
                Department.id != dept_id
            ).first()
            if existing:
                raise DuplicateResourceException(f"Department '{dept_in.name}' already exists.")
            dept.name = dept_in.name.strip()

        if dept_in.description is not None:
            dept.description = dept_in.description.strip()

        db.commit()
        db.refresh(dept)
        return dept

    @staticmethod
    def delete_department(db: Session, dept_id: int) -> bool:
        dept = DepartmentService.get_department_by_id(db, dept_id)
        assigned_employees = db.query(Employee).filter(Employee.department_id == dept_id).count()
        if assigned_employees > 0:
            raise PayrollException(
                f"Cannot delete department '{dept.name}' because {assigned_employees} employees are currently assigned to it.",
                status_code=400
            )
        db.delete(dept)
        db.commit()
        return True

    # Designation sub-operations
    @staticmethod
    def get_all_designations(db: Session, department_id: Optional[int] = None) -> List[Designation]:
        query = db.query(Designation)
        if department_id:
            query = query.filter(Designation.department_id == department_id)
        return query.order_by(Designation.title.asc()).all()

    @staticmethod
    def get_designation_by_id(db: Session, desig_id: int) -> Designation:
        desig = db.query(Designation).filter(Designation.id == desig_id).first()
        if not desig:
            raise ResourceNotFoundException("Designation", desig_id)
        return desig

    @staticmethod
    def create_designation(db: Session, desig_in: DesignationCreate) -> Designation:
        existing = db.query(Designation).filter(
            func.lower(Designation.title) == desig_in.title.strip().lower()
        ).first()
        if existing:
            raise DuplicateResourceException(f"Designation '{desig_in.title}' already exists.")

        if desig_in.department_id:
            DepartmentService.get_department_by_id(db, desig_in.department_id)

        desig = Designation(
            title=desig_in.title.strip(),
            department_id=desig_in.department_id,
            description=desig_in.description.strip() if desig_in.description else None
        )
        db.add(desig)
        db.commit()
        db.refresh(desig)
        return desig

    @staticmethod
    def update_designation(db: Session, desig_id: int, desig_in: DesignationUpdate) -> Designation:
        desig = DepartmentService.get_designation_by_id(db, desig_id)
        if desig_in.title:
            existing = db.query(Designation).filter(
                func.lower(Designation.title) == desig_in.title.strip().lower(),
                Designation.id != desig_id
            ).first()
            if existing:
                raise DuplicateResourceException(f"Designation '{desig_in.title}' already exists.")
            desig.title = desig_in.title.strip()

        if desig_in.department_id is not None:
            if desig_in.department_id > 0:
                DepartmentService.get_department_by_id(db, desig_in.department_id)
                desig.department_id = desig_in.department_id
            else:
                desig.department_id = None

        if desig_in.description is not None:
            desig.description = desig_in.description.strip()

        db.commit()
        db.refresh(desig)
        return desig

    @staticmethod
    def delete_designation(db: Session, desig_id: int) -> bool:
        desig = DepartmentService.get_designation_by_id(db, desig_id)
        assigned_employees = db.query(Employee).filter(Employee.designation_id == desig_id).count()
        if assigned_employees > 0:
            raise PayrollException(
                f"Cannot delete designation '{desig.title}' because {assigned_employees} employees are currently assigned to it.",
                status_code=400
            )
        db.delete(desig)
        db.commit()
        return True
