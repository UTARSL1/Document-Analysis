"""
Hybrid OCR/HTR extraction task - orchestrates the complete processing pipeline.
"""
from celery import Task
from .celery_app import celery_app
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.database import SessionLocal
from backend.app.models import Document, Template, ZoneData, Artifact
from backend.app.storage import get_storage
from backend.app.config import settings
from worker.tasks.template_matching import match_template
from worker.tasks.field_classifier import classify_field
from worker.htr.trocr_engine import get_trocr_engine
from PIL import Image
from io import BytesIO
from uuid import UUID
import json
from datetime import datetime

# PaddleOCR for printed text
try:
    from paddleocr import PaddleOCR
    PADDLE_OCR_AVAILABLE = True
except ImportError:
    PADDLE_OCR_AVAILABLE = False
    print("Warning: PaddleOCR not available, using fallback")


@celery_app.task(bind=True, name="hybrid_extraction")
def hybrid_extraction_task(self: Task, document_id: str):
    """
    Perform hybrid OCR/HTR extraction on a document.
    
    This is the CORE processing task that:
    1. Loads template for document type
    2. Matches document to template and aligns
    3. Extracts zones from template
    4. Classifies each zone as printed or handwritten
    5. Routes to appropriate engine (PaddleOCR or TrOCR)
    6. Validates extracted data
    7. Generates searchable PDF
    8. Creates structured JSON output
    9. Flags low-confidence results for manual review
    
    Args:
        document_id: UUID of the document to process
    """
    db = SessionLocal()
    
    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == UUID(document_id)).first()
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        
        # Update status
        document.status = "ocr_pending"
        db.commit()
        
        # Load template for document type
        template = db.query(Template).filter(
            Template.doc_type == document.doc_type,
            Template.is_active == True
        ).first()
        
        if not template:
            raise ValueError(f"No active template found for doc_type: {document.doc_type}")
        
        # Load document image
        storage = get_storage()
        image_data = storage.load(document.original_path)
        image = Image.open(BytesIO(image_data))
        
        # Step 1: Template matching and alignment
        template_config = {
            'anchor_points': template.anchor_points,
            'zones': template.zones
        }
        match_result = match_template(image, template_config)
        
        if not match_result['matched']:
            document.status = "ocr_failed"
            document.error_message = "Template matching failed"
            db.commit()
            return {"error": "Template matching failed"}
        
        aligned_zones = match_result['aligned_zones']
        
        # Step 2: Process each zone
        zone_results = []
        low_confidence_count = 0
        
        # Initialize engines
        if PADDLE_OCR_AVAILABLE:
            paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        htr_engine = get_trocr_engine(
            model_name=settings.HTR_MODEL,
            use_gpu=settings.HTR_USE_GPU
        )
        
        for zone in aligned_zones:
            zone_name = zone.get('name', 'unknown')
            bbox = zone.get('bbox', [])
            
            if len(bbox) != 4:
                continue
            
            x1, y1, x2, y2 = bbox
            
            # Extract zone image
            zone_img = image.crop((x1, y1, x2, y2))
            
            # Step 3: Classify field type
            classification = classify_field(image, bbox)
            is_handwritten = classification['is_handwritten']
            
            # Step 4: Route to appropriate engine
            if is_handwritten:
                # Use TrOCR for handwritten text
                ocr_result = htr_engine.recognize(zone_img)
                extracted_text = ocr_result['text']
                confidence = ocr_result['confidence']
            else:
                # Use PaddleOCR for printed text
                if PADDLE_OCR_AVAILABLE:
                    result = paddle_ocr.ocr(np.array(zone_img), cls=True)
                    if result and result[0]:
                        # Combine all text from zone
                        texts = [line[1][0] for line in result[0]]
                        extracted_text = ' '.join(texts)
                        # Average confidence
                        confidences = [line[1][1] for line in result[0]]
                        confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    else:
                        extracted_text = ""
                        confidence = 0.0
                else:
                    # Fallback: use TrOCR for everything
                    ocr_result = htr_engine.recognize(zone_img)
                    extracted_text = ocr_result['text']
                    confidence = ocr_result['confidence'] * 0.9  # Reduce confidence for fallback
            
            # Step 5: Validate extracted data
            validation_rules = zone.get('validation', {})
            validation_status = validate_zone_data(extracted_text, validation_rules)
            
            # Flag low confidence
            threshold = settings.HTR_CONFIDENCE_THRESHOLD if is_handwritten else settings.OCR_CONFIDENCE_THRESHOLD
            if confidence < threshold or validation_status == 'failed':
                low_confidence_count += 1
            
            # Store zone data
            zone_data = ZoneData(
                document_id=UUID(document_id),
                zone_name=zone_name,
                extracted_text=extracted_text,
                confidence=confidence,
                bbox=bbox,
                validation_status=validation_status,
                is_handwritten=is_handwritten
            )
            db.add(zone_data)
            
            zone_results.append({
                'zone_name': zone_name,
                'bbox': bbox,
                'text': extracted_text,
                'confidence': confidence,
                'validation_status': validation_status,
                'is_handwritten': is_handwritten
            })
        
        # Step 6: Generate structured JSON
        json_output = {
            'document_id': document_id,
            'document_type': document.doc_type,
            'processing_metadata': {
                'template_version': template.version,
                'template_match_confidence': match_result['confidence'],
                'processed_at': datetime.utcnow().isoformat(),
                'ocr_model': 'paddleocr' if PADDLE_OCR_AVAILABLE else 'trocr-fallback',
                'htr_model': settings.HTR_MODEL
            },
            'zones': zone_results
        }
        
        # Save JSON to storage
        json_path = f"json/{document.doc_type}/{datetime.now().strftime('%Y/%m/%d')}/{document_id}.json"
        json_bytes = BytesIO(json.dumps(json_output, indent=2).encode('utf-8'))
        json_full_path = storage.save(json_bytes, json_path)
        
        # Step 7: Create artifact record
        artifact = Artifact(
            document_id=UUID(document_id),
            json_path=json_full_path,
            json_data=json_output
            # TODO: Generate searchable PDF
        )
        db.add(artifact)
        
        # Step 8: Update document status
        # Flag for manual review if too many low-confidence zones
        if low_confidence_count > len(zone_results) * 0.3:  # More than 30% low confidence
            document.status = "ocr_manual_review"
        else:
            document.status = "ocr_completed"
        
        db.commit()
        
        # Trigger PDF generation
        from .pdf_generation import generate_searchable_pdf_task
        generate_searchable_pdf_task.delay(document_id)
        
        return {
            'document_id': document_id,
            'status': document.status,
            'zones_processed': len(zone_results),
            'low_confidence_count': low_confidence_count
        }
        
    except Exception as e:
        db.rollback()
        # Update document with error
        document = db.query(Document).filter(Document.id == UUID(document_id)).first()
        if document:
            document.status = "ocr_failed"
            document.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()


def validate_zone_data(text: str, validation_rules: dict) -> str:
    """
    Validate extracted text against validation rules.
    
    Args:
        text: Extracted text
        validation_rules: Validation rules from template
        
    Returns:
        str: 'passed', 'failed', or 'manual_review'
    """
    if not validation_rules:
        return 'passed'
    
    # Check if required
    if validation_rules.get('required', False) and not text:
        return 'failed'
    
    # Check pattern (regex)
    pattern = validation_rules.get('pattern')
    if pattern:
        import re
        if not re.match(pattern, text):
            return 'manual_review'
    
    # Check length
    min_length = validation_rules.get('min_length', 0)
    max_length = validation_rules.get('max_length', float('inf'))
    if not (min_length <= len(text) <= max_length):
        return 'manual_review'
    
    return 'passed'
