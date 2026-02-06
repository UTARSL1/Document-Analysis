"""
Field classifier to detect printed vs handwritten text.

Uses a simple heuristic-based approach for MVP.
For production, replace with a trained CNN classifier.
"""
import cv2
import numpy as np
from PIL import Image


def classify_field(image: Image.Image, bbox: list) -> dict:
    """
    Classify a field/zone as printed or handwritten.
    
    Uses heuristic features:
    - Stroke width variance (handwritten has more variance)
    - Character spacing uniformity (printed is more uniform)
    - Edge density (handwritten has more irregular edges)
    
    Args:
        image: PIL Image object
        bbox: Bounding box [x1, y1, x2, y2]
        
    Returns:
        dict: {
            'is_handwritten': bool,
            'confidence': float,
            'features': dict
        }
    """
    # Extract zone from image
    x1, y1, x2, y2 = bbox
    img_array = np.array(image.convert('L'))
    zone = img_array[y1:y2, x1:x2]
    
    if zone.size == 0:
        return {
            'is_handwritten': False,
            'confidence': 0.0,
            'features': {}
        }
    
    # Feature 1: Stroke width variance
    edges = cv2.Canny(zone, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) > 0:
        stroke_widths = [cv2.arcLength(c, True) / len(c) if len(c) > 0 else 0 for c in contours]
        stroke_variance = np.std(stroke_widths) if len(stroke_widths) > 0 else 0
    else:
        stroke_variance = 0
    
    # Feature 2: Edge density (irregular edges indicate handwriting)
    edge_density = np.sum(edges > 0) / edges.size
    
    # Feature 3: Horizontal projection variance (handwritten has more variance)
    horizontal_projection = np.sum(zone < 128, axis=1)
    projection_variance = np.std(horizontal_projection)
    
    # Simple heuristic scoring
    # High stroke variance + high edge density + high projection variance = handwritten
    handwritten_score = (
        (stroke_variance / 10.0) * 0.4 +
        (edge_density * 100) * 0.3 +
        (projection_variance / 100.0) * 0.3
    )
    
    # Threshold at 0.5
    is_handwritten = handwritten_score > 0.5
    confidence = handwritten_score if is_handwritten else (1 - handwritten_score)
    
    return {
        'is_handwritten': is_handwritten,
        'confidence': min(confidence, 0.95),  # Cap at 0.95 since this is heuristic
        'features': {
            'stroke_variance': float(stroke_variance),
            'edge_density': float(edge_density),
            'projection_variance': float(projection_variance),
            'handwritten_score': float(handwritten_score)
        }
    }
