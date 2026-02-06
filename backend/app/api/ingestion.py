"""
Document ingestion endpoints for batch uploads.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from ..database import get_db
from ..models import Document
from ..schemas import DocumentResponse
from ..storage import get_storage
from ..config import settings
import os

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    batch_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a single document for processing.
    
    Args:
        file: Document file (PDF, TIFF, JPG, PNG)
        doc_type: Document type (must match one of 12-16 configured types)
        batch_id: Optional batch identifier
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.tiff', '.tif', '.jpg', '.jpeg', '.png']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate unique document ID
    doc_id = uuid4()
    
    # Save file to storage
    storage = get_storage()
    storage_path = f"originals/{doc_type}/{datetime.now().strftime('%Y/%m/%d')}/{doc_id}{file_ext}"
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    # Save to storage
    from io import BytesIO
    full_path = storage.save(BytesIO(file_content), storage_path)
    
    # Create database record
    document = Document(
        id=doc_id,
        original_filename=file.filename,
        doc_type=doc_type,
        batch_id=batch_id,
        status="ingested",
        storage_backend=settings.STORAGE_BACKEND,
        original_path=full_path,
        file_size_bytes=file_size
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Trigger QC verification task
    # Trigger QC verification task
    from celery import Celery
    # Initialize minimal Celery client with just the broker
    celery_client = Celery("ingestion_producer", broker=settings.CELERY_BROKER_URL)
    celery_client.send_task("qc_verification", args=[str(document.id)], queue="qc_queue")
    
    return document


@router.post("/batch-upload")
async def batch_upload(
    files: list[UploadFile] = File(...),
    doc_type: str = Form(...),
    batch_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload multiple documents in a batch.
    """
    if not batch_id:
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    uploaded_docs = []
    for file in files:
        try:
            doc = await upload_document(file, doc_type, batch_id, db)
            uploaded_docs.append(doc)
        except Exception as e:
            # Log error but continue with other files
            print(f"Error uploading {file.filename}: {e}")
    
    return {
        "batch_id": batch_id,
        "total_files": len(files),
        "uploaded": len(uploaded_docs),
        "documents": uploaded_docs
    }
