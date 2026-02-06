"""
SQLAlchemy database models for document digitization system.
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, TIMESTAMP, ForeignKey, BigInteger, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .database import Base


class Document(Base):
    """Main document table with partitioning by document type."""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename = Column(String(512), nullable=False)
    doc_type = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="ingested", index=True)
    # Status values: ingested, qc_pending, qc_passed, qc_failed, correction_pending, 
    #                ocr_pending, ocr_completed, verified, archived
    batch_id = Column(String(255), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    error_message = Column(Text)
    file_size_bytes = Column(BigInteger)
    storage_backend = Column(String(50), nullable=False)
    original_path = Column(String(1024))
    
    # Relationships
    qc_verification = relationship("QCVerification", back_populates="document", uselist=False)
    correction_logs = relationship("CorrectionLog", back_populates="document")
    zone_data = relationship("ZoneData", back_populates="document")
    artifacts = relationship("Artifact", back_populates="document")


class QCVerification(Base):
    """Quality check verification results."""
    __tablename__ = "qc_verification"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    qc_status = Column(String(50), nullable=False, index=True)  # passed, failed, manual_review
    resolution_dpi = Column(Integer)
    skew_angle = Column(Float)
    contrast_score = Column(Float)
    border_check_passed = Column(Boolean)
    completeness_check_passed = Column(Boolean)
    evidence_path = Column(String(1024))  # Path to QC evidence PDF/images
    evidence_json = Column(JSONB)  # Detailed QC metrics
    verified_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    verified_by = Column(String(255))  # 'automated' or operator ID
    notes = Column(Text)
    
    # Relationship
    document = relationship("Document", back_populates="qc_verification")


class CorrectionLog(Base):
    """Log of corrections made to documents."""
    __tablename__ = "correction_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    correction_type = Column(String(100), nullable=False)  # rotate, crop, brightness, contrast, rescan
    operator_id = Column(String(255))
    before_path = Column(String(1024))
    after_path = Column(String(1024))
    correction_params = Column(JSONB)  # e.g., {"rotation_degrees": 90, "crop_bbox": [x1,y1,x2,y2]}
    corrected_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    
    # Relationship
    document = relationship("Document", back_populates="correction_logs")


class Template(Base):
    """Document templates for zone-based extraction."""
    __tablename__ = "templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_type = Column(String(100), nullable=False, unique=True)
    version = Column(Integer, nullable=False, default=1)
    zones = Column(JSONB, nullable=False)  # Array of zone definitions with bbox, name, type
    validation_rules = Column(JSONB)  # Validation rules per zone
    anchor_points = Column(JSONB)  # Key points for template matching
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class ZoneData(Base):
    """Extracted OCR/HTR data per zone."""
    __tablename__ = "zone_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    zone_name = Column(String(255), nullable=False)
    extracted_text = Column(Text)
    confidence = Column(Float)
    bbox = Column(ARRAY(Integer))  # [x1, y1, x2, y2]
    validation_status = Column(String(50), index=True)  # passed, failed, manual_review
    parsed_value = Column(JSONB)  # Structured parsed value (e.g., date as ISO string)
    is_handwritten = Column(Boolean)  # True if HTR was used, False if OCR
    extracted_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    
    # Relationship
    document = relationship("Document", back_populates="zone_data")


class Artifact(Base):
    """Generated artifacts (searchable PDFs, JSON outputs)."""
    __tablename__ = "artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    searchable_pdf_path = Column(String(1024))
    json_path = Column(String(1024))
    json_data = Column(JSONB)  # Full structured output
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    
    # Relationship
    document = relationship("Document", back_populates="artifacts")
