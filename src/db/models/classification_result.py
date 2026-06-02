from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from src.db.base import Base


class ClassificationResult(Base):
    __tablename__ = "classification_results"

    id = Column(Integer, primary_key=True, index=True)

    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    confidence = Column(Float, nullable=False)
    method = Column(String, nullable=False)
    reason = Column(Text, nullable=True)

    entities_json = Column(JSONB, nullable=True)
    similar_emails_json = Column(JSONB, nullable=True)

    corrected_subject = Column(Text, nullable=True)
    corrected_body = Column(Text, nullable=True)
    grammar_issues_found = Column(Boolean, default=False, nullable=False)
    grammar_corrections = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
