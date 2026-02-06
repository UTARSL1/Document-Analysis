"""
Template management endpoints for document type templates.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from ..database import get_db
from ..models import Template
from ..schemas import TemplateCreate, TemplateResponse

router = APIRouter()


@router.get("/", response_model=List[TemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    """
    List all document templates.
    """
    templates = db.query(Template).filter(Template.is_active == True).all()
    return templates


@router.get("/{doc_type}", response_model=TemplateResponse)
def get_template(doc_type: str, db: Session = Depends(get_db)):
    """
    Get template for a specific document type.
    """
    template = db.query(Template).filter(
        Template.doc_type == doc_type,
        Template.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found for doc_type: {doc_type}")
    
    return template


@router.post("/", response_model=TemplateResponse)
def create_template(template_data: TemplateCreate, db: Session = Depends(get_db)):
    """
    Create a new document template.
    """
    # Check if template already exists
    existing = db.query(Template).filter(Template.doc_type == template_data.doc_type).first()
    if existing:
        # Deactivate old template
        existing.is_active = False
    
    # Create new template
    template = Template(
        doc_type=template_data.doc_type,
        version=template_data.version,
        zones=[zone.dict() for zone in template_data.zones],
        validation_rules=template_data.validation_rules,
        anchor_points=template_data.anchor_points,
        is_active=True
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(template_id: UUID, template_data: TemplateCreate, db: Session = Depends(get_db)):
    """
    Update an existing template.
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.zones = [zone.dict() for zone in template_data.zones]
    template.validation_rules = template_data.validation_rules
    template.anchor_points = template_data.anchor_points
    template.version += 1
    
    db.commit()
    db.refresh(template)
    
    return template


@router.delete("/{template_id}")
def delete_template(template_id: UUID, db: Session = Depends(get_db)):
    """
    Deactivate a template (soft delete).
    """
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.is_active = False
    db.commit()
    
    return {"status": "deleted", "template_id": str(template_id)}
