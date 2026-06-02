from sqlalchemy.orm import Session

from src.db.models.classification_result import ClassificationResult


class ClassificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        email_id: int,
        category_id: int,
        confidence: float,
        method: str,
        reason: str,
        entities_json: dict,
        similar_emails_json: list,
        corrected_subject: str = None,
        corrected_body: str = None,
        grammar_issues_found: bool = False,
        grammar_corrections: list = None,
    ) -> ClassificationResult:
        result = ClassificationResult(
            email_id=email_id,
            category_id=category_id,
            confidence=confidence,
            method=method,
            reason=reason,
            entities_json=entities_json,
            similar_emails_json=similar_emails_json,
            corrected_subject=corrected_subject,
            corrected_body=corrected_body,
            grammar_issues_found=grammar_issues_found,
            grammar_corrections=grammar_corrections or [],
        )

        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        return result
