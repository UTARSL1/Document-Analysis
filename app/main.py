import json
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import get_db
from .models import Document, Artifact
from .schemas import DocumentResponse, DocumentDetailResponse
from .worker import celery_app
from processing.processing import safe_filename

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
DOC_TYPES_PATH = Path(os.getenv("DOC_TYPES_PATH", "/app/config/doc_types.json"))

app = FastAPI(title="Document Digitization MVP")

templates = Jinja2Templates(directory="/app/templates")


def load_doc_types() -> List[dict]:
    if DOC_TYPES_PATH.exists():
        return json.loads(DOC_TYPES_PATH.read_text())
    return []


@app.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return RedirectResponse(url="/upload")


@app.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "doc_types": load_doc_types()},
    )


@app.post("/upload")
def upload_document(
    request: Request,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if not doc_type:
        raise HTTPException(status_code=400, detail="Document type is required")
    if not file.filename:
        raise HTTPException(status_code=400, detail="File is required")

    document_id = str(uuid.uuid4())
    original_filename = safe_filename(file.filename)
    upload_dir = UPLOAD_DIR / document_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / original_filename

    with file_path.open("wb") as buffer:
        buffer.write(file.file.read())

    document = Document(
        id=document_id,
        original_filename=original_filename,
        doc_type=doc_type,
        status="queued",
    )
    db.add(document)
    db.commit()

    celery_app.send_task("process_document", args=[document_id])

    return RedirectResponse(url=f"/documents/{document_id}", status_code=303)


@app.get("/documents", response_class=HTMLResponse)
def list_documents(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    documents = db.query(Document).order_by(Document.created_at.desc()).all()
    return templates.TemplateResponse(
        "documents.html",
        {"request": request, "documents": documents},
    )


@app.get("/documents/{document_id}", response_class=HTMLResponse)
def document_detail(
    request: Request, document_id: str, db: Session = Depends(get_db)
) -> HTMLResponse:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    artifact = (
        db.query(Artifact)
        .filter(Artifact.document_id == document_id)
        .order_by(Artifact.id.desc())
        .first()
    )
    return templates.TemplateResponse(
        "document_detail.html",
        {"request": request, "document": document, "artifact": artifact},
    )


@app.get("/api/documents", response_model=List[DocumentResponse])
def api_list_documents(db: Session = Depends(get_db)) -> List[DocumentResponse]:
    return db.query(Document).order_by(Document.created_at.desc()).all()


@app.get("/api/documents/{document_id}", response_model=DocumentDetailResponse)
def api_document_detail(document_id: str, db: Session = Depends(get_db)) -> DocumentDetailResponse:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.get("/documents/{document_id}/download/pdf")
def download_pdf(document_id: str, db: Session = Depends(get_db)) -> FileResponse:
    artifact = (
        db.query(Artifact)
        .filter(Artifact.document_id == document_id)
        .order_by(Artifact.id.desc())
        .first()
    )
    if not artifact or not artifact.searchable_pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available")
    return FileResponse(artifact.searchable_pdf_path, filename="searchable.pdf")


@app.get("/documents/{document_id}/download/json")
def download_json(document_id: str, db: Session = Depends(get_db)) -> FileResponse:
    artifact = (
        db.query(Artifact)
        .filter(Artifact.document_id == document_id)
        .order_by(Artifact.id.desc())
        .first()
    )
    if not artifact or not artifact.json_path:
        raise HTTPException(status_code=404, detail="JSON not available")
    return FileResponse(artifact.json_path, filename="output.json")
