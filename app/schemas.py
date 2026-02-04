from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class DocumentCreate(BaseModel):
    doc_type: str


class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    doc_type: str
    created_at: datetime
    status: str
    error_message: Optional[str]

    class Config:
        from_attributes = True


class PageResponse(BaseModel):
    id: int
    page_no: int
    width: int
    height: int

    class Config:
        from_attributes = True


class ArtifactResponse(BaseModel):
    id: int
    searchable_pdf_path: Optional[str]
    json_path: Optional[str]
    extracted_json: Optional[Any]

    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    pages: List[PageResponse] = []
    artifacts: List[ArtifactResponse] = []
