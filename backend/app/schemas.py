"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# Document Schemas
class DocumentBase(BaseModel):
    original_filename: str
    doc_type: str
    batch_id: Optional[str] = None


class DocumentCreate(DocumentBase):
    storage_backend: str
    original_path: str
    file_size_bytes: int


class DocumentResponse(DocumentBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# QC Verification Schemas
class QCVerificationResponse(BaseModel):
    id: UUID
    document_id: UUID
    qc_status: str
    resolution_dpi: Optional[int]
    skew_angle: Optional[float]
    contrast_score: Optional[float]
    border_check_passed: Optional[bool]
    completeness_check_passed: Optional[bool]
    evidence_path: Optional[str]
    evidence_json: Optional[Dict[str, Any]]
    verified_at: datetime
    verified_by: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


# Zone Data Schemas
class ZoneDataResponse(BaseModel):
    id: UUID
    zone_name: str
    extracted_text: Optional[str]
    confidence: Optional[float]
    bbox: Optional[List[int]]
    validation_status: Optional[str]
    parsed_value: Optional[Dict[str, Any]]
    is_handwritten: Optional[bool]
    
    model_config = ConfigDict(from_attributes=True)


# Template Schemas
class TemplateZone(BaseModel):
    name: str
    bbox: List[int]  # [x1, y1, x2, y2]
    type: str  # text, date, alphanumeric, numeric
    description: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None


class TemplateCreate(BaseModel):
    doc_type: str
    version: int = 1
    zones: List[TemplateZone]
    validation_rules: Optional[Dict[str, Any]] = None
    anchor_points: Optional[List[Dict[str, Any]]] = None


class TemplateResponse(BaseModel):
    id: UUID
    doc_type: str
    version: int
    zones: List[Dict[str, Any]]
    validation_rules: Optional[Dict[str, Any]]
    anchor_points: Optional[List[Dict[str, Any]]]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Artifact Schemas
class ArtifactResponse(BaseModel):
    id: UUID
    document_id: UUID
    searchable_pdf_path: Optional[str]
    json_path: Optional[str]
    json_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Document Detail Response (with all related data)
class DocumentDetailResponse(DocumentResponse):
    qc_verification: Optional[QCVerificationResponse] = None
    zone_data: List[ZoneDataResponse] = []
    artifacts: List[ArtifactResponse] = []


# Pagination
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
