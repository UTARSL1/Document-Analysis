"""
Quality check endpoints for QC verification and manual review.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from uuid import UUID
from ..database import get_db
from ..models import QCVerification, Document
from ..schemas import QCVerificationResponse
import math

router = APIRouter()


@router.get("/queue")
def get_qc_queue(
    status: Optional[str] = Query("manual_review"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get QC queue for manual review.
    
    Args:
        status: QC status filter (manual_review, failed, passed)
        page: Page number
        page_size: Items per page
    """
    query = db.query(QCVerification).join(Document)
    
    if status:
        query = query.filter(QCVerification.qc_status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    qc_items = query.order_by(desc(QCVerification.verified_at)).offset(offset).limit(page_size).all()
    
    return {
        "items": qc_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size)
    }


@router.get("/stats")
def get_qc_stats(db: Session = Depends(get_db)):
    """
    Get QC statistics.
    """
    total = db.query(QCVerification).count()
    passed = db.query(QCVerification).filter(QCVerification.qc_status == "passed").count()
    failed = db.query(QCVerification).filter(QCVerification.qc_status == "failed").count()
    manual_review = db.query(QCVerification).filter(QCVerification.qc_status == "manual_review").count()
    
    auto_pass_rate = (passed / total * 100) if total > 0 else 0
    
    return {
        "total_verified": total,
        "passed": passed,
        "failed": failed,
        "manual_review": manual_review,
        "auto_pass_rate": round(auto_pass_rate, 2)
    }


@router.get("/{document_id}", response_model=QCVerificationResponse)
def get_qc_verification(document_id: UUID, db: Session = Depends(get_db)):
    """
    Get QC verification details for a document.
    """
    qc = db.query(QCVerification).filter(QCVerification.document_id == document_id).first()
    if not qc:
        raise HTTPException(status_code=404, detail="QC verification not found")
    
    return qc


@router.post("/{document_id}/approve")
def approve_qc(document_id: UUID, operator_id: str, db: Session = Depends(get_db)):
    """
    Manually approve a document that was flagged for review.
    """
    qc = db.query(QCVerification).filter(QCVerification.document_id == document_id).first()
    if not qc:
        raise HTTPException(status_code=404, detail="QC verification not found")
    
    qc.qc_status = "passed"
    qc.verified_by = operator_id
    
    # Update document status
    document = db.query(Document).filter(Document.id == document_id).first()
    if document:
        document.status = "qc_passed"
    
    db.commit()
    
    # Trigger OCR/HTR processing
    # Trigger OCR/HTR processing
    from celery import Celery
    from ..config import settings
    # Initialize minimal Celery client
    celery_client = Celery("qc_producer", broker=settings.CELERY_BROKER_URL)
    celery_client.send_task("hybrid_extraction", args=[str(document_id)], queue="ocr_queue")
    
    return {"status": "approved", "document_id": str(document_id)}


@router.post("/{document_id}/reject")
def reject_qc(document_id: UUID, operator_id: str, reason: str, db: Session = Depends(get_db)):
    """
    Reject a document and mark for correction or re-scan.
    """
    qc = db.query(QCVerification).filter(QCVerification.document_id == document_id).first()
    if not qc:
        raise HTTPException(status_code=404, detail="QC verification not found")
    
    qc.qc_status = "failed"
    qc.verified_by = operator_id
    qc.notes = reason
    
    # Update document status
    document = db.query(Document).filter(Document.id == document_id).first()
    if document:
        document.status = "qc_failed"
        document.error_message = reason
    
    db.commit()
    
    return {"status": "rejected", "document_id": str(document_id), "reason": reason}
