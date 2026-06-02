from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core import config
from src.db.session import get_db
from src.services.email_processing_service import EmailProcessingService

router = APIRouter(
    prefix="/processing",
    tags=["Processing"],
)


@router.post("/process-next")
def process_next_emails(
    limit: int = config.PROCESSING_CONCURRENCY,
    db: Session = Depends(get_db),
):
    service = EmailProcessingService(db)

    return service.process_next_emails(limit=limit)


@router.post("/process-all")
def process_all_emails(
    batch_size: int = config.PROCESSING_CONCURRENCY,
    db: Session = Depends(get_db),
):
    service = EmailProcessingService(db)

    return service.process_all_emails(batch_size=batch_size)
