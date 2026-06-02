from pathlib import Path

from sqlalchemy.orm import Session

from src.core.parser.email_parser import EmailParser
from src.db.repositories.email_repository import EmailRepository


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.parser = EmailParser()
        self.email_repository = EmailRepository(db)

    def ingest_inbox(self, inbox_path: str = "src/data/inbox") -> dict:
        inbox_dir = Path(inbox_path)

        if not inbox_dir.exists():
            return {
                "status": "error",
                "message": f"Inbox directory not found: {inbox_path}",
            }

        saved = 0
        skipped = 0
        results = []

        for file_path in inbox_dir.iterdir():
            if not file_path.is_file():
                continue

            parsed = self.parser.parse(file_path)

            existing = self.email_repository.get_by_source_path(
                parsed["source_path"]
            )

            if existing:
                skipped += 1
                continue

            email = self.email_repository.create_from_parser_result(parsed)

            saved += 1

            results.append(
                {
                    "id": email.id,
                    "filename": email.filename,
                    "status": email.status,
                    "is_garbage": email.is_garbage,
                }
            )

        return {
            "saved": saved,
            "skipped": skipped,
            "results": results,
        }
