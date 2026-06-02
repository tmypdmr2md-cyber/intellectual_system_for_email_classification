from typing import Optional

from sqlalchemy.orm import Session

from src.db.models.email import Email


class EmailRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_from_parser_result(self, parsed: dict) -> Email:
        email = Email(
            source_path=parsed["source_path"],
            filename=parsed["filename"],
            extension=parsed.get("extension"),
            file_type=parsed.get("file_type"),
            status=parsed["status"],
            is_garbage=parsed["is_garbage"],
            raw_text=parsed.get("raw_text"),
            parsed_json=parsed,
            processing_status="parsed",
        )

        self.db.add(email)
        self.db.commit()
        self.db.refresh(email)

        return email

    def get_by_source_path(self, source_path: str) -> Optional[Email]:
        return (
            self.db
            .query(Email)
            .filter(Email.source_path == source_path)
            .first()
        )

    def get_unprocessed_emails(self, limit: int = 10) -> list[Email]:
        return (
            self.db
            .query(Email)
            .filter(Email.processing_status == "parsed")
            .filter(Email.is_garbage.is_(False))
            .limit(limit)
            .all()
        )

    def mark_processing(self, email: Email) -> None:
        email.processing_status = "processing"
        self.db.commit()

    def mark_classified(self, email: Email) -> None:
        email.processing_status = "classified"
        self.db.commit()

    def mark_failed(self, email: Email) -> None:
        email.processing_status = "failed"
        self.db.commit()
