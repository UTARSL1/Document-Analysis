"""
Skew angle detection check.
"""
import cv2
import numpy as np
from PIL import Image
from backend.app.config import settings


def detect_skew(image: Image.Image) -> dict:
    """
    Detect skew angle of the document.
    
    Uses Hough Line Transform to detect dominant lines and calculate skew.
    
    Args:
        image: PIL Image object
        
    Returns:
        dict: {
            'passed': bool,
            'angle': float,
            'message': str
        }
    """
    # Convert PIL image to OpenCV format
    img_array = np.array(image.convert('L'))
    
    # Edge detection
    edges = cv2.Canny(img_array, 50, 150, apertureSize=3)
    
    # Detect lines using Hough Transform
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is None:
        return {
            'passed': True,
            'angle': 0.0,
            'message': "No lines detected, assuming no skew"
        }
    
    # Calculate angles
    angles = []
    for rho, theta in lines[:, 0]:
        angle = np.degrees(theta) - 90
        if abs(angle) < 45:  # Only consider angles close to horizontal
            angles.append(angle)
    
    if not angles:
        skew_angle = 0.0
    else:
        # Use median to be robust against outliers
        skew_angle = float(np.median(angles))
    
    # Check against threshold
    max_skew = settings.QC_MAX_SKEW_ANGLE
    passed = abs(skew_angle) <= max_skew
    
    return {
        'passed': passed,
        'angle': round(skew_angle, 2),
        'max_allowed': max_skew,
        'message': f"Skew angle {skew_angle:.2f}° {'within' if passed else 'exceeds'} limit {max_skew}°"
    }
