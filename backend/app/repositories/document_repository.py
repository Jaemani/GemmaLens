from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.dictionary import DictionaryItem
from app.models.document import Document
from app.schemas.document_schema import DocumentCreate


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: DocumentCreate) -> Document:
        document = Document(title=data.title, source_type=data.source_type, content=data.content)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def list(self) -> list[Document]:
        return list(self.db.scalars(select(Document).order_by(Document.created_at.desc())))

    def get(self, document_id: str) -> Document | None:
        return self.db.get(Document, document_id)

    def delete(self, document_id: str) -> bool:
        document = self.get(document_id)
        if not document:
            return False
        self.db.execute(delete(Analysis).where(Analysis.document_id == document_id))
        self.db.execute(update(DictionaryItem).where(DictionaryItem.document_id == document_id).values(document_id=None))
        self.db.delete(document)
        self.db.commit()
        return True
