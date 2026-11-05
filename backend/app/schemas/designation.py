from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DesignationBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    department_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=255)


class DesignationCreate(DesignationBase):
    pass


class DesignationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=100)
    department_id: Optional[int] = None
    description: Optional[str] = Field(None, max_length=255)


class DesignationResponse(DesignationBase):
    id: int
    department_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
