import uuid
from datetime import date as _date
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AssetTypeCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class AssetTypeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class AssetTypeResponse(ORMModel):
    id: uuid.UUID
    name: str


class AssetCreateRequest(BaseModel):
    asset_type_id: uuid.UUID
    asset_tag: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=150)
    purchase_date: _date | None = None
    warranty_expiry: _date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AssetUpdateRequest(BaseModel):
    asset_type_id: uuid.UUID | None = None
    asset_tag: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    purchase_date: _date | None = None
    warranty_expiry: _date | None = None
    status: str | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AssetResponse(BaseModel):
    id: uuid.UUID
    asset_type_id: uuid.UUID
    asset_type_name: str
    asset_tag: str
    name: str
    purchase_date: _date | None
    warranty_expiry: _date | None
    status: str
    notes: str | None
    current_employee_id: uuid.UUID | None
    current_employee_name: str | None


class AssignAssetRequest(BaseModel):
    employee_id: uuid.UUID


class AssetAssignmentResponse(ORMModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    asset_tag: str
    asset_name: str
    employee_id: uuid.UUID
    employee_name: str
    assigned_at: datetime
    returned_at: datetime | None


class AssetSummaryResponse(BaseModel):
    total: int
    available: int
    assigned: int
    retired: int
    lost: int
    damaged: int
