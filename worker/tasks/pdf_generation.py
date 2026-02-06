"""
Searchable PDF generation task.

Creates a searchable PDF with invisible OCR/HTR text layer.
"""
from celery import Task
from .celery_app import celery_app
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.database import SessionLocal
from backend.app.models import Document, Artifact, ZoneData
from backend.app.storage import get_storage
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from uuid import UUID
from datetime import datetime
import json

# Try to import OCRmyPDF (optional dependency)
try:
    import ocrmypdf
    OCRMYPDF_AVAILABLE = True
except ImportError:
    OCRMYPDF_AVAILABLE = False
    print("Warning: OCRmyPDF not available, using fallback PDF generation")

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader


@celery_app.task(bind=True, name="generate_searchable_pdf")
def generate_searchable_pdf_task(self: Task, document_id: str):
    """
    Generate searchable PDF with OCR/HTR text layer.
    
    Args:
        document_id: UUID of the document
    """
    db = SessionLocal()
    
    try:
        # Get document and zone data
        document = db.query(Document).filter(Document.id == UUID(document_id)).first()
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        
        zone_data = db.query(ZoneData).filter(ZoneData.document_id == UUID(document_id)).all()
        
        # Load original image
        storage = get_storage()
        image_data = storage.load(document.original_path)
        image = Image.open(BytesIO(image_data))
        
        # Generate PDF with text layer
        pdf_path = f"searchable_pdf/{document.doc_type}/{datetime.now().strftime('%Y/%m/%d')}/{document_id}.pdf"
        
        # Create PDF with invisible text layer
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=(image.width, image.height))
        
        # Draw image
        img_reader = ImageReader(image)
        c.drawImage(img_reader, 0, 0, width=image.width, height=image.height)
        
        # Add invisible text layer at zone positions
        c.setFillColorRGB(0, 0, 0, alpha=0)  # Invisible text
        c.setFont("Helvetica", 12)
        
        for zone in zone_data:
            if zone.extracted_text and zone.bbox:
                x1, y1, x2, y2 = zone.bbox
                # PDF coordinates are bottom-left origin, image is top-left
                pdf_y = image.height - y2
                
                # Draw invisible text at zone position
                c.drawString(x1, pdf_y, zone.extracted_text)
        
        c.save()
        pdf_buffer.seek(0)
        
        # Save to storage
        pdf_full_path = storage.save(pdf_buffer, pdf_path)
        
        # Update artifact record
        artifact = db.query(Artifact).filter(Artifact.document_id == UUID(document_id)).first()
        if artifact:
            artifact.searchable_pdf_path = pdf_full_path
        else:
            artifact = Artifact(
                document_id=UUID(document_id),
                searchable_pdf_path=pdf_full_path
            )
            db.add(artifact)
        
        db.commit()
        
        return {
            'document_id': document_id,
            'pdf_path': pdf_full_path,
            'zones_embedded': len(zone_data)
        }
        
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()
