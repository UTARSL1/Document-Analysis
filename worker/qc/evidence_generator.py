"""
QC evidence generator - creates annotated images and reports.
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime


def generate_evidence(image: Image.Image, qc_results: dict, document_id: str, storage) -> str:
    """
    Generate QC verification evidence with annotated image and metrics.
    
    Creates a visual report showing:
    - Original image
    - QC check results overlaid
    - Metrics summary
    
    Args:
        image: Original PIL Image
        qc_results: Dictionary of QC check results
        document_id: Document UUID
        storage: Storage backend instance
        
    Returns:
        str: Path to stored evidence file
    """
    # Create a copy for annotation
    evidence_img = image.copy().convert('RGB')
    draw = ImageDraw.Draw(evidence_img)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw QC results on image
    y_offset = 30
    for check_name, result in qc_results.items():
        passed = result.get('passed', False)
        color = (0, 255, 0) if passed else (255, 0, 0)
        status = "✓" if passed else "✗"
        text = f"{status} {check_name.upper()}: {result.get('message', '')}"
        draw.text((10, y_offset), text, fill=color, font=small_font)
        y_offset += 30
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((10, evidence_img.height - 40), f"Verified: {timestamp}", fill=(255, 255, 255), font=small_font)
    
    # Convert to bytes
    buffer = BytesIO()
    evidence_img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    
    # Save to storage
    evidence_path = f"qc_evidence/{datetime.now().strftime('%Y/%m/%d')}/{document_id}_evidence.jpg"
    full_path = storage.save(buffer, evidence_path)
    
    return full_path
