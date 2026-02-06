"""
Contrast/brightness check.
"""
import cv2
import numpy as np
from PIL import Image
from backend.app.config import settings


def check_contrast(image: Image.Image) -> dict:
    """
    Check image contrast quality.
    
    Uses standard deviation of pixel intensities as a contrast metric.
    
    Args:
        image: PIL Image object
        
    Returns:
        dict: {
            'passed': bool,
            'score': float,
            'message': str
        }
    """
    # Convert to grayscale
    img_array = np.array(image.convert('L'))
    
    # Calculate contrast score (normalized standard deviation)
    std_dev = np.std(img_array)
    contrast_score = std_dev / 128.0  # Normalize to 0-1 range
    
    # Check against threshold
    min_contrast = settings.QC_MIN_CONTRAST_SCORE
    passed = contrast_score >= min_contrast
    
    return {
        'passed': passed,
        'score': round(contrast_score, 3),
        'min_required': min_contrast,
        'message': f"Contrast score {contrast_score:.3f} {'meets' if passed else 'below'} minimum {min_contrast}"
    }
