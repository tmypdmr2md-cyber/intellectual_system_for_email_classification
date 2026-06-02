from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models.category import Category
from src.db.models.classification_result import ClassificationResult
from src.db.models.email import Email
from src.db.models.email_embedding import EmailEmbedding
from src.db.init_db import reset_db
from src.db.session import get_db


router = APIRouter(
    tags=["DataBase"],
)

inbox_dir = Path("src/data/inbox")


@router.get("/db/overview")
def get_overview(db: Session = Depends(get_db)):
    return {
        "total_emails": db.query(Email).count(),
        "classified": (
            db.query(Email)
            .filter(Email.processing_status == "classified")
            .count()
        ),
        "pending": (
            db.query(Email)
            .filter(Email.processing_status == "parsed")
            .filter(Email.is_garbage.is_(False))
            .count()
        ),
        "failed": (
            db.query(Email)
            .filter(Email.processing_status == "failed")
            .count()
        ),
        "garbage": (
            db.query(Email)
            .filter(Email.is_garbage.is_(True))
            .count()
        ),
        "categories": db.query(Category).count(),
        "embeddings": db.query(EmailEmbedding).count(),
        "classification_results": db.query(ClassificationResult).count(),
        "inbox_files": len([path for path in inbox_dir.iterdir() if path.is_file()])
        if inbox_dir.exists()
        else 0,
    }


@router.post("/db/reset")
def reset_database(db: Session = Depends(get_db)):
    db.close()
    reset_db()

    return {
        "status": "ok",
        "message": "Database was dropped and recreated",
    }


@router.get("/db/inbox-files")
def get_inbox_files(db: Session = Depends(get_db)):
    saved_by_path = {
        item.source_path: item
        for item in db.query(Email).all()
    }

    files = []
    if not inbox_dir.exists():
        return files

    for path in sorted(inbox_dir.iterdir()):
        if not path.is_file():
            continue

        saved = saved_by_path.get(str(path))
        files.append(
            {
                "filename": path.name,
                "source_path": str(path),
                "extension": path.suffix or None,
                "size_bytes": path.stat().st_size,
                "ingested": saved is not None,
                "email_id": saved.id if saved else None,
                "status": saved.status if saved else "not_ingested",
                "processing_status": saved.processing_status if saved else None,
                "is_garbage": saved.is_garbage if saved else None,
            }
        )

    return files


@router.get("/categories/list")
def list_categories(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Category,
            func.count(ClassificationResult.id).label("emails_count"),
        )
        .outerjoin(ClassificationResult, ClassificationResult.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
        .all()
    )

    return [
        {
            "id": category.id,
            "name": category.name,
            "title": category.title,
            "description": category.description,
            "is_default": category.is_default,
            "created_by": category.created_by,
            "emails_count": emails_count,
        }
        for category, emails_count in rows
    ]


@router.get("/categories/{category_id}/emails")
def list_category_emails(category_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Email, ClassificationResult)
        .join(ClassificationResult, ClassificationResult.email_id == Email.id)
        .filter(ClassificationResult.category_id == category_id)
        .order_by(ClassificationResult.created_at.desc())
        .all()
    )

    return [
        _serialize_email_summary(email, classification)
        for email, classification in rows
    ]


@router.get("/classification-results/list")
def list_classification_results(limit: int = 100, db: Session = Depends(get_db)):
    rows = (
        db.query(ClassificationResult, Email, Category)
        .join(Email, Email.id == ClassificationResult.email_id)
        .join(Category, Category.id == ClassificationResult.category_id)
        .order_by(ClassificationResult.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": result.id,
            "email_id": email.id,
            "filename": email.filename,
            "category": category.name,
            "confidence": result.confidence,
            "method": result.method,
            "reason": result.reason,
            "corrected_subject": result.corrected_subject,
            "corrected_body": result.corrected_body,
            "grammar_issues_found": result.grammar_issues_found,
            "grammar_corrections": result.grammar_corrections or [],
            "created_at": _iso(result.created_at),
        }
        for result, email, category in rows
    ]


def latest_classification_subquery(db: Session):
    return (
        db.query(
            ClassificationResult.email_id.label("email_id"),
            func.max(ClassificationResult.id).label("classification_id"),
        )
        .group_by(ClassificationResult.email_id)
        .subquery()
    )


def get_latest_classification(
    db: Session,
    email_id: int,
) -> Optional[tuple[ClassificationResult, Category]]:
    return (
        db.query(ClassificationResult, Category)
        .join(Category, Category.id == ClassificationResult.category_id)
        .filter(ClassificationResult.email_id == email_id)
        .order_by(ClassificationResult.id.desc())
        .first()
    )


def _serialize_email_summary(
    email: Email,
    classification: Optional[ClassificationResult] = None,
    category: Optional[Category] = None,
) -> dict:
    parsed = email.parsed_json or {}
    parsed_email = parsed.get("email") or {}

    return {
        "id": email.id,
        "filename": email.filename,
        "subject": parsed_email.get("subject") or "Без темы",
        "sender": parsed_email.get("sender") or {},
        "status": email.status,
        "is_garbage": email.is_garbage,
        "processing_status": email.processing_status,
        "category": category.name if category else None,
        "confidence": classification.confidence if classification else None,
        "method": classification.method if classification else None,
        "grammar_issues_found": classification.grammar_issues_found if classification else False,
        "created_at": _iso(email.created_at),
        "updated_at": _iso(email.updated_at),
    }


def _iso(value):
    return value.isoformat() if value else None
