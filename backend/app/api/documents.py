"""
Document retrieval and management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID
from ..database import get_db
from ..models import Document, QCVerification, ZoneData, Artifact
from ..schemas import DocumentResponse, DocumentDetailResponse, PaginatedResponse
from ..storage import get_storage
import math

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    doc_type: Optional[str] = None,
    batch_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List documents with pagination and filtering.
    """
    query = db.query(Document)
    
    # Apply filters
    if status:
        query = query.filter(Document.status == status)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if batch_id:
        query = query.filter(Document.batch_id == batch_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    documents = query.order_by(desc(Document.created_at)).offset(offset).limit(page_size).all()
    
    return {
        "items": documents,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size)
    }


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    """
    Get document details including QC verification, zone data, and artifacts.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document


@router.get("/{document_id}/download-pdf")
def download_pdf(document_id: UUID, db: Session = Depends(get_db)):
    """
    Get download URL for searchable PDF.
    """
    artifact = db.query(Artifact).filter(Artifact.document_id == document_id).first()
    if not artifact or not artifact.searchable_pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    storage = get_storage()
    url = storage.get_url(artifact.searchable_pdf_path, expires_in=3600)
    
    return {"download_url": url}


@router.get("/{document_id}/download-json")
def download_json(document_id: UUID, db: Session = Depends(get_db)):
    """
    Get JSON output for document.
    """
    artifact = db.query(Artifact).filter(Artifact.document_id == document_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="JSON not found")
    
    return artifact.json_data
