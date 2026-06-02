from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from src.db.base import Base


class EmailEmbedding(Base):
    __tablename__ = "email_embeddings"

    id = Column(Integer, primary_key=True, index=True)

    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)

    embedding = Column(JSONB, nullable=False)
    model_name = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
