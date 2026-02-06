"""
Automated quality check verification task.

This is the PRIMARY task that runs automated QC checks on ingested documents.
Target: < 1 second per page for automated checks.
"""
from celery import Task
from .celery_app import celery_app
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.database import SessionLocal
from backend.app.models import Document, QCVerification
from backend.app.storage import get_storage
from backend.app.config import settings
from worker.qc.resolution_check import check_resolution
from worker.qc.skew_detection import detect_skew
from worker.qc.border_check import check_borders
from worker.qc.contrast_check import check_contrast
from worker.qc.completeness import check_completeness
from worker.qc.evidence_generator import generate_evidence
from PIL import Image
from io import BytesIO
from uuid import UUID
import json


@celery_app.task(bind=True, name="qc_verification")
def qc_verification_task(self: Task, document_id: str):
    """
    Perform automated quality verification on a document.
    
    Steps:
    1. Load document from storage
    2. Run automated QC checks (resolution, skew, borders, contrast, completeness)
    3. Generate verification evidence
    4. Determine pass/fail/manual_review status
    5. Update database with results
    6. Trigger next step (OCR/HTR) if passed
    
    Args:
        document_id: UUID of the document to verify
    """
    db = SessionLocal()
    
    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == UUID(document_id)).first()
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        
        # Update document status
        document.status = "qc_pending"
        db.commit()
        
        # Load document from storage
        storage = get_storage()
        image_data = storage.load(document.original_path)
        image = Image.open(BytesIO(image_data))
        
        # Run QC checks
        qc_results = {}
        
        # 1. Resolution check
        resolution_result = check_resolution(image)
        qc_results['resolution'] = resolution_result
        
        # 2. Skew detection
        skew_result = detect_skew(image)
        qc_results['skew'] = skew_result
        
        # 3. Border check
        border_result = check_borders(image)
        qc_results['borders'] = border_result
        
        # 4. Contrast check
        contrast_result = check_contrast(image)
        qc_results['contrast'] = contrast_result
        
        # 5. Completeness check
        completeness_result = check_completeness(image)
        qc_results['completeness'] = completeness_result
        
        # Determine overall QC status
        critical_checks = ['resolution', 'completeness']
        critical_passed = all(qc_results[check]['passed'] for check in critical_checks)
        all_passed = all(result['passed'] for result in qc_results.values())
        
        if critical_passed and all_passed:
            qc_status = "passed"
        elif not critical_passed:
            qc_status = "failed"
        else:
            # Some non-critical checks failed, flag for manual review
            qc_status = "manual_review"
        
        # Generate evidence
        evidence_path = generate_evidence(
            image,
            qc_results,
            document_id,
            storage
        )
        
        # Create QC verification record
        qc_verification = QCVerification(
            document_id=UUID(document_id),
            qc_status=qc_status,
            resolution_dpi=qc_results['resolution'].get('dpi'),
            skew_angle=qc_results['skew'].get('angle'),
            contrast_score=qc_results['contrast'].get('score'),
            border_check_passed=qc_results['borders']['passed'],
            completeness_check_passed=qc_results['completeness']['passed'],
            evidence_path=evidence_path,
            evidence_json=qc_results,
            verified_by="automated"
        )
        
        db.add(qc_verification)
        
        # Update document status
        if qc_status == "passed":
            document.status = "qc_passed"
            # Trigger OCR/HTR processing
            from .hybrid_extraction import hybrid_extraction_task
            hybrid_extraction_task.delay(document_id)
        elif qc_status == "failed":
            document.status = "qc_failed"
            document.error_message = "Automated QC checks failed"
        else:
            document.status = "qc_manual_review"
        
        db.commit()
        
        return {
            "document_id": document_id,
            "qc_status": qc_status,
            "results": qc_results
        }
        
    except Exception as e:
        db.rollback()
        # Update document with error
        document = db.query(Document).filter(Document.id == UUID(document_id)).first()
        if document:
            document.status = "qc_failed"
            document.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()
