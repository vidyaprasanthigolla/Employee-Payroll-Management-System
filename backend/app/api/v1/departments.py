from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.services.department_service import DepartmentService
from app.core.dependencies import require_authenticated, require_admin

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=List[DepartmentResponse], summary="List all departments")
def list_departments(
    db: Session = Depends(get_db),
    current_user=Depends(require_authenticated)
):
    """Retrieves all registered company departments."""
    return DepartmentService.get_all_departments(db)


@router.get("/{dept_id}", response_model=DepartmentResponse, summary="Get department details by ID")
def get_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_authenticated)
):
    return DepartmentService.get_department_by_id(db, dept_id)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, summary="Create a new department (Admin only)")
def create_department(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):
    return DepartmentService.create_department(db, dept_in)


@router.put("/{dept_id}", response_model=DepartmentResponse, summary="Update department (Admin only)")
def update_department(
    dept_id: int,
    dept_in: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):
    return DepartmentService.update_department(db, dept_id, dept_in)


@router.delete("/{dept_id}", summary="Delete department (Admin only)")
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):
    DepartmentService.delete_department(db, dept_id)
    return {"message": f"Department ID {dept_id} deleted successfully."}
