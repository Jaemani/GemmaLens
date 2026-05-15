from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.session import get_db
from app.repositories.document_repository import DocumentRepository
from app.schemas.document_schema import DocumentCreate, DocumentListItem, DocumentRead
from app.services.document_ingestion_service import DocumentIngestionError, DocumentIngestionService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRead)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    return DocumentRepository(db).create(payload)


@router.post("/upload", response_model=DocumentRead)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        payload = await DocumentIngestionService().from_upload(file)
    except DocumentIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
    return DocumentRepository(db).create(payload)


@router.get("", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)):
    documents = DocumentRepository(db).list()
    return [
        DocumentListItem(
            id=document.id,
            title=document.title,
            source_type=document.source_type,
            preview=document.content[:220],
            created_at=document.created_at,
        )
        for document in documents
    ]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    return document
