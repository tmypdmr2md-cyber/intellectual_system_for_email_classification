from typing import Optional

from sqlalchemy.orm import Session

from src.core.config import DEFAULT_CATEGORIES
from src.db.models.category import Category


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Optional[Category]:
        return (
            self.db
            .query(Category)
            .filter(Category.name == name)
            .first()
        )

    def list_names(self) -> list[str]:
        return [
            name
            for (name,) in self.db.query(Category.name).order_by(Category.name).all()
        ]

    def create(
        self,
        name: str,
        title: str,
        description: str = "",
        is_default: bool = False,
        created_by: str = "system",
    ) -> Category:
        category = Category(
            name=name,
            title=title,
            description=description,
            is_default=is_default,
            created_by=created_by,
        )

        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)

        return category

    def get_or_create(
        self,
        name: str,
        title: str,
        description: str = "",
        is_default: bool = False,
        created_by: str = "system",
    ) -> Category:
        category = self.get_by_name(name)

        if category:
            return category

        return self.create(
            name=name,
            title=title,
            description=description,
            is_default=is_default,
            created_by=created_by,
        )

    def ensure_default_categories(self) -> None:
        for item in DEFAULT_CATEGORIES:
            category = self.get_by_name(item["name"])
            if category:
                category.title = item["title"]
                category.description = item["description"]
                category.is_default = True
                category.created_by = category.created_by or "system"
                continue

            self.db.add(
                Category(
                    name=item["name"],
                    title=item["title"],
                    description=item["description"],
                    is_default=True,
                    created_by="system",
                )
            )

        self.db.commit()
