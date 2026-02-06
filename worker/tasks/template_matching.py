"""
Template matching engine for document alignment.
"""
import cv2
import numpy as np
from PIL import Image
from typing import Optional, Dict, List


def match_template(image: Image.Image, template_config: dict) -> dict:
    """
    Match document to template and calculate alignment transformation.
    
    Uses anchor points (logos, headers, borders) to detect and align document.
    
    Args:
        image: PIL Image object
        template_config: Template configuration with anchor_points
        
    Returns:
        dict: {
            'matched': bool,
            'confidence': float,
            'transformation': dict,  # rotation, scale, translation
            'aligned_zones': list  # Adjusted zone bboxes
        }
    """
    img_array = np.array(image.convert('L'))
    
    # Get anchor points from template
    anchor_points = template_config.get('anchor_points', [])
    zones = template_config.get('zones', [])
    
    if not anchor_points:
        # No anchor points, assume document is already aligned
        return {
            'matched': True,
            'confidence': 0.7,
            'transformation': {
                'rotation': 0,
                'scale': 1.0,
                'translation': [0, 0]
            },
            'aligned_zones': zones
        }
    
    # For MVP, use simple feature matching
    # In production, use ORB/SIFT feature matching with reference template images
    
    # Detect key features in the image
    orb = cv2.ORB_create(nfeatures=500)
    keypoints, descriptors = orb.detectAndCompute(img_array, None)
    
    if descriptors is None or len(keypoints) < 10:
        # Not enough features, assume no match
        return {
            'matched': False,
            'confidence': 0.0,
            'transformation': None,
            'aligned_zones': zones
        }
    
    # For MVP, assume document is roughly aligned
    # Calculate simple rotation correction using Hough lines
    edges = cv2.Canny(img_array, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    rotation_angle = 0
    if lines is not None and len(lines) > 0:
        angles = []
        for rho, theta in lines[:10, 0]:
            angle = np.degrees(theta) - 90
            if abs(angle) < 10:  # Only consider small rotations
                angles.append(angle)
        if angles:
            rotation_angle = np.median(angles)
    
    # Apply rotation to zone bboxes
    height, width = img_array.shape
    center = (width // 2, height // 2)
    
    aligned_zones = []
    for zone in zones:
        bbox = zone.get('bbox', [])
        if len(bbox) == 4:
            # For small rotations, approximate bbox adjustment
            # In production, use proper affine transformation
            aligned_zones.append({
                **zone,
                'bbox': bbox,  # Keep original for MVP
                'rotation_applied': rotation_angle
            })
        else:
            aligned_zones.append(zone)
    
    return {
        'matched': True,
        'confidence': 0.85,  # Heuristic confidence
        'transformation': {
            'rotation': float(rotation_angle),
            'scale': 1.0,
            'translation': [0, 0]
        },
        'aligned_zones': aligned_zones
    }
