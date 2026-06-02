from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.routes.db import (
    _serialize_email_summary,
    get_latest_classification,
    latest_classification_subquery,
)
from src.db.models.category import Category
from src.db.models.classification_result import ClassificationResult
from src.db.models.email import Email
from src.db.session import get_db
from src.services.ingestion_service import IngestionService

router = APIRouter(
    prefix="/emails",
    tags=["Emails"],
)

inbox_dir = Path("src/data/inbox")


@router.post("/ingest")
def ingest_emails(db: Session = Depends(get_db)):
    service = IngestionService(db)
    return service.ingest_inbox(inbox_path=inbox_dir)


@router.get("/list")
def list_emails(
    status: str = "all",
    limit: int = 200,
    db: Session = Depends(get_db),
):
    latest = latest_classification_subquery(db)

    query = (
        db.query(Email, ClassificationResult, Category)
        .outerjoin(latest, latest.c.email_id == Email.id)
        .outerjoin(
            ClassificationResult,
            ClassificationResult.id == latest.c.classification_id,
        )
        .outerjoin(Category, Category.id == ClassificationResult.category_id)
        .order_by(Email.id)
    )

    if status == "parsed":
        query = query.filter(
            Email.processing_status == "parsed",
            Email.is_garbage.is_(False),
        )
    elif status == "classified":
        query = query.filter(Email.processing_status == "classified")
    elif status == "garbage":
        query = query.filter(Email.is_garbage.is_(True))
    elif status == "failed":
        query = query.filter(Email.processing_status == "failed")

    rows = query.limit(limit).all()

    return [
        _serialize_email_summary(email, classification, category)
        for email, classification, category in rows
    ]


@router.get("/{email_id}")
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    latest = get_latest_classification(db, email_id=email.id)
    classification = None
    category = None

    if latest:
        classification, category = latest

    result = _serialize_email_summary(email, classification, category)
    result["source_path"] = email.source_path
    result["extension"] = email.extension
    result["file_type"] = email.file_type
    result["raw_text"] = email.raw_text
    result["parsed_json"] = email.parsed_json

    if classification:
        result["classification"] = {
            "id": classification.id,
            "category": category.name if category else None,
            "confidence": classification.confidence,
            "method": classification.method,
            "reason": classification.reason,
            "entities": classification.entities_json,
            "similar_emails": classification.similar_emails_json,
            "corrected_subject": classification.corrected_subject,
            "corrected_body": classification.corrected_body,
            "grammar_issues_found": classification.grammar_issues_found,
            "grammar_corrections": classification.grammar_corrections or [],
            "created_at": classification.created_at.isoformat()
            if classification.created_at
            else None,
        }
    else:
        result["classification"] = None

    return result
