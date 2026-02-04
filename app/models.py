from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    original_filename = Column(String, nullable=False)
    doc_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, nullable=False, default="queued")
    error_message = Column(Text, nullable=True)

    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    page_no = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    document = relationship("Document", back_populates="pages")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    searchable_pdf_path = Column(String, nullable=True)
    json_path = Column(String, nullable=True)
    extracted_json = Column(JSONB, nullable=True)

    document = relationship("Document", back_populates="artifacts")
