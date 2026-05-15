from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.session import get_db
from app.repositories.document_repository import DocumentRepository
from app.schemas.document_schema import DocumentCreate, DocumentListItem, DocumentRead
from app.services.document_ingestion_service import DocumentIngestionError, DocumentIngestionService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRead)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    return _read_document(DocumentRepository(db).create(payload))


@router.post("/upload", response_model=DocumentRead)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        payload = await DocumentIngestionService().from_upload(file)
    except DocumentIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None
    return _read_document(DocumentRepository(db).create(payload))


@router.post("/{document_id}/file", response_model=DocumentRead)
async def attach_document_file(document_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    name = file.filename or "uploaded-file"
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in {"pdf", "docx", "txt", "md", "markdown"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOCX, TXT, and Markdown files can be attached as source files.",
        )
    raw = await file.read()
    service = DocumentIngestionService()
    path = service.save_original_file(raw, extension)
    if not path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file was empty.")
    source_type = "pdf" if extension == "pdf" else "docx" if extension == "docx" else "markdown" if extension in {"md", "markdown"} else "text"
    document = DocumentRepository(db).attach_original_file(document_id, path, file.content_type, source_type=source_type)
    if not document:
        raise not_found("Document not found")
    return _read_document(document)


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


@router.get("/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    if not document.original_file_path:
        raise not_found("Original file not stored")
    path = Path(document.original_file_path)
    if not path.exists() or not path.is_file():
        raise not_found("Original file not found")
    return FileResponse(path, media_type=document.original_mime_type or "application/octet-stream", filename=document.title)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    return _read_document(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    deleted = DocumentRepository(db).delete(document_id)
    if not deleted:
        raise not_found("Document not found")


def _read_document(document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        title=document.title,
        source_type=document.source_type,
        content=document.content,
        has_original_file=bool(document.original_file_path),
        original_mime_type=document.original_mime_type,
        created_at=document.created_at,
    )
