"""
Completeness check for missing corners or tears.
"""
import cv2
import numpy as np
from PIL import Image


def check_completeness(image: Image.Image) -> dict:
    """
    Check if document is complete (no missing corners or major tears).
    
    Detects if the document has all four corners and no large missing regions.
    
    Args:
        image: PIL Image object
        
    Returns:
        dict: {
            'passed': bool,
            'content_percentage': float,
            'corners_detected': int,
            'message': str
        }
    """
    # Convert to grayscale
    img_array = np.array(image.convert('L'))
    height, width = img_array.shape
    
    # Threshold to binary
    _, binary = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Calculate content percentage (non-white pixels)
    content_pixels = np.count_nonzero(binary < 200)
    total_pixels = height * width
    content_percentage = (content_pixels / total_pixels) * 100
    
    # Detect corners using Harris corner detection
    corners = cv2.cornerHarris(img_array, 2, 3, 0.04)
    corners = cv2.dilate(corners, None)
    
    # Count significant corners in each quadrant
    corner_threshold = 0.01 * corners.max()
    corner_points = np.where(corners > corner_threshold)
    
    # Divide image into 4 quadrants and check for corners
    h_mid, w_mid = height // 2, width // 2
    quadrants = [
        (0, h_mid, 0, w_mid),  # Top-left
        (0, h_mid, w_mid, width),  # Top-right
        (h_mid, height, 0, w_mid),  # Bottom-left
        (h_mid, height, w_mid, width)  # Bottom-right
    ]
    
    corners_detected = 0
    for y1, y2, x1, x2 in quadrants:
        quadrant_corners = np.sum(
            (corner_points[0] >= y1) & (corner_points[0] < y2) &
            (corner_points[1] >= x1) & (corner_points[1] < x2)
        )
        if quadrant_corners > 0:
            corners_detected += 1
    
    # Check if document is complete
    min_content = 95.0  # At least 95% content
    min_corners = 3  # At least 3 corners detected
    
    passed = content_percentage >= min_content and corners_detected >= min_corners
    
    return {
        'passed': passed,
        'content_percentage': round(content_percentage, 2),
        'corners_detected': corners_detected,
        'min_content_required': min_content,
        'message': f"Content {content_percentage:.1f}%, {corners_detected}/4 corners - {'complete' if passed else 'incomplete'}"
    }
