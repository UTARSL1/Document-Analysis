"""
Resolution (DPI) verification check.
"""
from PIL import Image
from backend.app.config import settings


def check_resolution(image: Image.Image) -> dict:
    """
    Check if image resolution meets minimum DPI requirements.
    
    Args:
        image: PIL Image object
        
    Returns:
        dict: {
            'passed': bool,
            'dpi': int,
            'message': str
        }
    """
    # Get DPI from image info
    dpi = image.info.get('dpi', (72, 72))
    if isinstance(dpi, tuple):
        dpi = max(dpi)  # Use the higher of horizontal/vertical DPI
    
    # Check against threshold
    min_dpi = settings.QC_MIN_DPI
    passed = dpi >= min_dpi
    
    return {
        'passed': passed,
        'dpi': int(dpi),
        'min_required': min_dpi,
        'message': f"DPI {dpi} {'meets' if passed else 'below'} minimum {min_dpi}"
    }
