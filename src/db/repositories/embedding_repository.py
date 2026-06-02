from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models.category import Category
from src.db.models.classification_result import ClassificationResult
from src.db.models.email_embedding import EmailEmbedding


class EmbeddingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        email_id: int,
        embedding: list,
        model_name: str,
    ) -> EmailEmbedding:
        item = EmailEmbedding(
            email_id=email_id,
            embedding=embedding,
            model_name=model_name,
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        return item

    def get_all(self) -> list[EmailEmbedding]:
        return self.db.query(EmailEmbedding).all()

    def get_all_with_categories(self) -> list[dict]:
        latest = (
            self.db.query(
                ClassificationResult.email_id.label("email_id"),
                func.max(ClassificationResult.id).label("classification_id"),
            )
            .group_by(ClassificationResult.email_id)
            .subquery()
        )

        rows = (
            self.db.query(EmailEmbedding, Category.name.label("category"))
            .outerjoin(latest, latest.c.email_id == EmailEmbedding.email_id)
            .outerjoin(
                ClassificationResult,
                ClassificationResult.id == latest.c.classification_id,
            )
            .outerjoin(Category, Category.id == ClassificationResult.category_id)
            .all()
        )

        return [
            {
                "email_id": embedding.email_id,
                "embedding": embedding.embedding,
                "category": category,
            }
            for embedding, category in rows
        ]
