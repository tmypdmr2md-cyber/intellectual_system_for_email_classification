from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from src.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    is_default = Column(Boolean, default=True)
    created_by = Column(String, default="system")

    created_at = Column(DateTime, default=datetime.utcnow)
