import os
from pathlib import Path
from celery import Celery
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Document, Artifact, Page
from processing.processing import process_document

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "/data/artifacts"))

celery_app = Celery("worker", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> None:
    db: Session = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return

        document.status = "processing"
        db.commit()

        input_path = UPLOAD_DIR / document_id / document.original_filename
        result = process_document(
            document_id=document_id,
            doc_type=document.doc_type,
            input_path=input_path,
            output_root=ARTIFACT_DIR,
        )

        artifact = Artifact(
            document_id=document_id,
            searchable_pdf_path=result["searchable_pdf_path"],
            json_path=result["json_path"],
            extracted_json=result["json_output"],
        )
        db.add(artifact)

        db.query(Page).filter(Page.document_id == document_id).delete()
        for page in result["json_output"]["pages"]:
            db.add(
                Page(
                    document_id=document_id,
                    page_no=page["page_no"],
                    width=page["width"],
                    height=page["height"],
                )
            )

        document.status = "completed"
        db.commit()
    except Exception as exc:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "failed"
            document.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()
