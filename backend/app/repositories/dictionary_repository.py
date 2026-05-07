from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dictionary import DictionaryItem
from app.schemas.dictionary_schema import DictionaryItemCreate


class DictionaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_or_increment(self, data: DictionaryItemCreate) -> DictionaryItem:
        existing = self.db.scalar(
            select(DictionaryItem).where(
                DictionaryItem.text == data.text,
                DictionaryItem.item_type == data.item_type,
            )
        )
        if existing:
            existing.encounter_count += 1
            existing.meaning = data.meaning or existing.meaning
            existing.source_sentence = data.source_sentence or existing.source_sentence
            existing.document_id = data.document_id or existing.document_id
            existing.notes = data.notes or existing.notes
            self.db.commit()
            self.db.refresh(existing)
            return existing
        item = DictionaryItem(**data.model_dump())
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self) -> list[DictionaryItem]:
        return list(self.db.scalars(select(DictionaryItem).order_by(DictionaryItem.created_at.desc())))

    def delete(self, item_id: str) -> bool:
        item = self.db.get(DictionaryItem, item_id)
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    def mark_viewed(self, item_id: str) -> DictionaryItem | None:
        item = self.db.get(DictionaryItem, item_id)
        if not item:
            return None
        item.view_count += 1
        item.last_viewed_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(item)
        return item
