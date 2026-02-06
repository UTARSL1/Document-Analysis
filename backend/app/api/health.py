"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..database import get_db
from ..config import settings

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Returns system health status including database connectivity.
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": settings.APP_VERSION,
        "database": db_status,
        "storage_backend": settings.STORAGE_BACKEND
    }


@router.get("/health/ready")
def readiness_check():
    """Readiness check for Kubernetes."""
    return {"ready": True}


@router.get("/health/live")
def liveness_check():
    """Liveness check for Kubernetes."""
    return {"alive": True}
