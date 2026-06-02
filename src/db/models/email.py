from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from src.db.base import Base


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)

    source_path = Column(String, unique=True, nullable=False)
    filename = Column(String, nullable=False)
    extension = Column(String, nullable=True)
    file_type = Column(String, nullable=True)

    status = Column(String, nullable=False)
    is_garbage = Column(Boolean, default=False)

    raw_text = Column(Text, nullable=True)
    parsed_json = Column(JSONB, nullable=False)

    processing_status = Column(String, default="parsed")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
