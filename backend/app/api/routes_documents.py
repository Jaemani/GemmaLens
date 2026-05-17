from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.session import get_db
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.section_analysis_repository import SectionAnalysisRepository
from app.schemas.document_schema import (
    DocumentCreate,
    DocumentListItem,
    DocumentRead,
    DocumentSectionRead,
    DuplicateDocumentCleanupItem,
    DuplicateDocumentCleanupResponse,
)
from app.services.academic_text_service import AcademicTextService
from app.services.document_ingestion_service import DocumentIngestionError, DocumentIngestionService
from app.services.document_section_service import DocumentSectionService

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


@router.post("/cleanup-duplicates", response_model=DuplicateDocumentCleanupResponse)
def cleanup_duplicate_documents(db: Session = Depends(get_db)):
    repository = DocumentRepository(db)
    groups: dict[tuple[str, str], list] = {}
    for document in repository.list():
        key = (document.source_type, document.title.strip().lower())
        groups.setdefault(key, []).append(document)

    cleaned: list[DuplicateDocumentCleanupItem] = []
    for rows in groups.values():
        if len(rows) <= 1:
            continue
        ranked = sorted(rows, key=lambda document: _document_cleanup_score(document, db), reverse=True)
        kept = ranked[0]
        deleted_ids: list[str] = []
        for duplicate in ranked[1:]:
            if repository.delete(duplicate.id):
                deleted_ids.append(duplicate.id)
        if deleted_ids:
            cleaned.append(
                DuplicateDocumentCleanupItem(
                    source_type=kept.source_type,
                    title=kept.title,
                    kept_document_id=kept.id,
                    deleted_document_ids=deleted_ids,
                )
            )
    return DuplicateDocumentCleanupResponse(groups=cleaned, deleted_count=sum(len(group.deleted_document_ids) for group in cleaned))


@router.get("", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)):
    documents = DocumentRepository(db).list()
    items: list[DocumentListItem] = []
    for document in documents:
        sections = _document_sections(document.content)
        analyzed_indices = _analyzed_section_indices(document.id, db)
        has_analysis = AnalysisRepository(db).get_result(document.id) is not None
        items.append(
            DocumentListItem(
                id=document.id,
                title=document.title,
                source_type=document.source_type,
                preview=document.content[:220],
                created_at=document.created_at,
                total_sections=len(sections),
                analyzed_sections=len(analyzed_indices),
                has_analysis=has_analysis,
            )
        )
    return items


@router.get("/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    if not document.original_file_path:
        raise not_found("Original file not stored")
    path = _resolve_original_file_path(document.original_file_path)
    if not path.exists() or not path.is_file():
        raise not_found("Original file not found")
    return FileResponse(path, media_type=document.original_mime_type or "application/octet-stream", filename=document.title)


@router.get("/{document_id}/sections", response_model=list[DocumentSectionRead])
def list_document_sections(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    sections = _document_sections(document.content)
    analyzed_indices = _analyzed_section_indices(document_id, db)
    return [_read_section(index, section, len(sections), analyzed=index in analyzed_indices) for index, section in enumerate(sections)]


@router.get("/{document_id}/sections/{section_index}", response_model=DocumentSectionRead)
def get_document_section(document_id: str, section_index: int, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    sections = _document_sections(document.content)
    if section_index < 0 or section_index >= len(sections):
        raise not_found("Document section not found")
    analyzed_indices = _analyzed_section_indices(document_id, db)
    return _read_section(section_index, sections[section_index], len(sections), analyzed=section_index in analyzed_indices)


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


def _resolve_original_file_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    candidates = [
        Path.cwd() / path,
        Path.cwd() / "backend" / path,
        Path(__file__).resolve().parents[2] / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _document_sections(content: str):
    readable_text = AcademicTextService().readable_section(content)
    return DocumentSectionService().split_with_labels(readable_text)


def _read_section(index: int, section, total: int, analyzed: bool = False) -> DocumentSectionRead:
    preview = " ".join(section.text.split())[:220]
    return DocumentSectionRead(
        index=index,
        section_number=index + 1,
        total_sections=total,
        text=section.text,
        preview=preview,
        char_count=len(section.text),
        analyzed=analyzed,
        source_label=section.source_label,
        title=section.title,
        continuation=section.continuation,
    )


def _analyzed_section_indices(document_id: str, db: Session) -> set[int]:
    indices = set(SectionAnalysisRepository(db).list_indices(document_id))
    if AnalysisRepository(db).get_result(document_id):
        indices.add(0)
    return indices


def _document_cleanup_score(document, db: Session) -> tuple[int, int, int, float]:
    sections = _document_sections(document.content)
    total = max(len(sections), 1)
    analyzed = len(_analyzed_section_indices(document.id, db))
    complete = 1 if total > 1 and analyzed >= total else 0
    has_analysis = 1 if AnalysisRepository(db).get_result(document.id) else 0
    return (complete, analyzed, has_analysis, document.created_at.timestamp())
