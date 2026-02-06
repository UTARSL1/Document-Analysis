"""
QC module initialization.
"""
from .resolution_check import check_resolution
from .skew_detection import detect_skew
from .border_check import check_borders
from .contrast_check import check_contrast
from .completeness import check_completeness
from .evidence_generator import generate_evidence

__all__ = [
    "check_resolution",
    "detect_skew",
    "check_borders",
    "check_contrast",
    "check_completeness",
    "generate_evidence"
]
