from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.designation import DesignationCreate, DesignationUpdate, DesignationResponse
from app.services.department_service import DepartmentService
from app.core.dependencies import require_authenticated, require_admin

router = APIRouter(prefix="/designations", tags=["Designations"])


@router.get("", response_model=List[DesignationResponse], summary="List designations")
def list_designations(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    db: Session = Depends(get_db),
    current_user=Depends(require_authenticated)
):
    """Retrieves designations, optionally filtered by department."""
    items = DepartmentService.get_all_designations(db, department_id=department_id)
    # Map department name for presentation
    result = []
    for d in items:
        result.append(
            DesignationResponse(
                id=d.id,
                title=d.title,
                department_id=d.department_id,
                department_name=d.department.name if d.department else None,
                description=d.description,
                created_at=d.created_at,
                updated_at=d.updated_at
            )
        )
    return result


@router.get("/{desig_id}", response_model=DesignationResponse, summary="Get designation by ID")
def get_designation(
    desig_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_authenticated)
):
    d = DepartmentService.get_designation_by_id(db, desig_id)
    return DesignationResponse(
        id=d.id,
        title=d.title,
        department_id=d.department_id,
        department_name=d.department.name if d.department else None,
        description=d.description,
        created_at=d.created_at,
        updated_at=d.updated_at
    )


@router.post("", response_model=DesignationResponse, status_code=status.HTTP_201_CREATED, summary="Create designation (Admin only)")
def create_designation(
    desig_in: DesignationCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):
    d = DepartmentService.create_designation(db, desig_in)
    return DesignationResponse(
        id=d.id,
        title=d.title,
        department_id=d.department_id,
        department_name=d.department.name if d.department else None,
        description=d.description,
        created_at=d.created_at,
        updated_at=d.updated_at
    )


@router.put("/{desig_id}", response_model=DesignationResponse, summary="Update designation (Admin only)")
def update_designation(
    desig_id: int,
    desig_in: DesignationUpdate,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):
    d = DepartmentService.update_designation(db, desig_id, desig_in)
    return DesignationResponse(
        id=d.id,
        title=d.title,
        department_id=d.department_id,
        department_name=d.department.name if d.department else None,
        description=d.description,
        created_at=d.created_at,
        updated_at=d.updated_at
    )


@router.delete("/{desig_id}", summary="Delete designation (Admin only)")
def delete_designation(
    desig_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin)
):
    DepartmentService.delete_designation(db, desig_id)
    return {"message": f"Designation ID {desig_id} deleted successfully."}
