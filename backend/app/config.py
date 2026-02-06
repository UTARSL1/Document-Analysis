"""
Configuration management for the document digitization system.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Document Digitization System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/document_digitization"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    
    # Redis/Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # Storage
    STORAGE_BACKEND: str = "s3"  # Options: local, s3, postgres
    LOCAL_STORAGE_PATH: str = "./storage"
    
    # S3/MinIO Configuration
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "document-digitization"
    S3_REGION: str = "us-east-1"
    
    # QC Thresholds
    QC_MIN_DPI: int = 300
    QC_MAX_SKEW_ANGLE: float = 2.0
    QC_MIN_CONTRAST_SCORE: float = 0.3
    QC_MAX_BORDER_PERCENTAGE: int = 10
    
    # HTR Configuration
    HTR_MODEL: str = "microsoft/trocr-large-handwritten"
    HTR_CONFIDENCE_THRESHOLD: float = 0.70
    HTR_AUTO_ACCEPT_THRESHOLD: float = 0.85
    HTR_USE_GPU: bool = True
    HTR_BATCH_SIZE: int = 8
    
    # OCR Configuration
    OCR_CONFIDENCE_THRESHOLD: float = 0.85
    
    # Processing
    MAX_WORKERS: int = 10
    PROCESSING_TIMEOUT: int = 300  # seconds
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
