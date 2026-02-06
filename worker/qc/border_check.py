"""
Border/crop verification check.
"""
import cv2
import numpy as np
from PIL import Image
from backend.app.config import settings


def check_borders(image: Image.Image) -> dict:
    """
    Check for excessive borders around the document.
    
    Detects large uniform regions at edges that indicate excessive borders.
    
    Args:
        image: PIL Image object
        
    Returns:
        dict: {
            'passed': bool,
            'border_percentage': float,
            'message': str
        }
    """
    # Convert to grayscale
    img_array = np.array(image.convert('L'))
    height, width = img_array.shape
    
    # Detect edges
    edges = cv2.Canny(img_array, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return {
            'passed': True,
            'border_percentage': 0.0,
            'message': "No content detected"
        }
    
    # Find largest contour (assumed to be document content)
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Calculate border percentage
    content_area = w * h
    total_area = width * height
    border_area = total_area - content_area
    border_percentage = (border_area / total_area) * 100
    
    # Check against threshold
    max_border = settings.QC_MAX_BORDER_PERCENTAGE
    passed = border_percentage <= max_border
    
    return {
        'passed': passed,
        'border_percentage': round(border_percentage, 2),
        'max_allowed': max_border,
        'content_bbox': [x, y, x + w, y + h],
        'message': f"Border {border_percentage:.1f}% {'within' if passed else 'exceeds'} limit {max_border}%"
    }
