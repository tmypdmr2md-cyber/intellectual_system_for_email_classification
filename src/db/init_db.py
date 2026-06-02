from src.db.base import Base
from src.db.session import SessionLocal, engine
from sqlalchemy import text

from src.db.models.email import Email
from src.db.models.category import Category
from src.db.models.classification_result import ClassificationResult
from src.db.models.email_embedding import EmailEmbedding
from src.db.repositories.category_repository import CategoryRepository


def init_db():
    Base.metadata.create_all(bind=engine)
    ensure_classification_result_columns()
    seed_default_categories()


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_default_categories()


def seed_default_categories():
    db = SessionLocal()

    try:
        CategoryRepository(db).ensure_default_categories()
    finally:
        db.close()


def ensure_classification_result_columns():
    statements = [
        "ALTER TABLE classification_results ADD COLUMN IF NOT EXISTS corrected_subject TEXT",
        "ALTER TABLE classification_results ADD COLUMN IF NOT EXISTS corrected_body TEXT",
        (
            "ALTER TABLE classification_results "
            "ADD COLUMN IF NOT EXISTS grammar_issues_found BOOLEAN NOT NULL DEFAULT false"
        ),
        "ALTER TABLE classification_results ADD COLUMN IF NOT EXISTS grammar_corrections JSONB",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


if __name__ == "__main__":
    init_db()
    print("Database tables created")
