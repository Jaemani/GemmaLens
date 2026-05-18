from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import not_found
from app.db.session import get_db
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.section_analysis_repository import SectionAnalysisRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.analysis_schema import (
    AnalysisResult,
    PageBatchAnalysisRequest,
    PageBatchAnalysisResponse,
    PaperMapResponse,
    StagedAnalysisRequest,
    StagedAnalysisResponse,
)
from app.services.academic_text_service import AcademicTextService
from app.services.analysis_normalization_service import AnalysisNormalizationService
from app.services.analysis_pipeline_service import AnalysisPipelineService
from app.services.document_section_service import DocumentSectionService
from app.services.paper_map_service import PaperMapService

router = APIRouter(prefix="/documents", tags=["analysis"])


@router.post("/{document_id}/analyze", response_model=AnalysisResult)
async def analyze_document(document_id: str, db: Session = Depends(get_db)):
    service = AnalysisPipelineService(DocumentRepository(db), AnalysisRepository(db))
    profile = UserProfileRepository(db).get_or_create()
    try:
        result = await service.analyze(
            document_id,
            target_level=profile.target_level,
            support_language=profile.support_language,
            learning_language=profile.learning_language,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if not result:
        raise not_found("Document not found")
    return result


@router.post("/{document_id}/sections/{section_index}/analyze", response_model=AnalysisResult)
async def analyze_document_section(document_id: str, section_index: int, force: bool = Query(False), db: Session = Depends(get_db)):
    service = AnalysisPipelineService(DocumentRepository(db), AnalysisRepository(db), SectionAnalysisRepository(db))
    profile = UserProfileRepository(db).get_or_create()
    try:
        result = await service.analyze_section(
            document_id,
            section_index,
            target_level=profile.target_level,
            support_language=profile.support_language,
            learning_language=profile.learning_language,
            force=force,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if not result:
        raise not_found("Document section not found")
    return result


@router.post("/{document_id}/pages/{page_number}/analyze", response_model=PageBatchAnalysisResponse)
async def analyze_document_page(document_id: str, page_number: int, db: Session = Depends(get_db)):
    if page_number <= 0:
        raise not_found("Document page not found")
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    readable_text = AcademicTextService().readable_section(document.content)
    sections = DocumentSectionService().split_with_labels(readable_text)
    pages = _learning_pages(sections)
    if page_number not in pages:
        raise not_found("Document page not found")
    service = AnalysisPipelineService(DocumentRepository(db), AnalysisRepository(db), SectionAnalysisRepository(db))
    profile = UserProfileRepository(db).get_or_create()
    try:
        results = await service.analyze_page_sections(
            document_id,
            page_number,
            target_level=profile.target_level,
            support_language=profile.support_language,
            learning_language=profile.learning_language,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if results is None:
        raise not_found("Document not found")
    analyzed = [index + 1 for index, _ in results]
    return PageBatchAnalysisResponse(
        document_id=document_id,
        total_pages=len(pages),
        total_sections=len(sections),
        requested_pages=[page_number],
        analyzed_pages=[page_number] if analyzed else [],
        analyzed_sections=analyzed,
        skipped_sections=sorted(index + 1 for index in SectionAnalysisRepository(db).list_indices(document_id) if index + 1 not in analyzed),
        status="completed" if analyzed else "nothing_to_do",
        message=f"Prepared page {page_number} with {len(analyzed)} section lesson(s)." if analyzed else f"No learning sections found on page {page_number}.",
    )


@router.get("/{document_id}/sections/{section_index}/analysis", response_model=AnalysisResult)
def get_document_section_analysis(document_id: str, section_index: int, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    readable_text = AcademicTextService().readable_section(document.content)
    section = DocumentSectionService().section(readable_text, section_index)
    if not section:
        raise not_found("Document section not found")
    section_text, section_count = section
    result = SectionAnalysisRepository(db).get_result(document_id, section_index)
    if not result and section_index == 0:
        result = AnalysisRepository(db).get_result(document_id)
    if not result:
        raise not_found("Section analysis not found")
    profile = UserProfileRepository(db).get_or_create()
    normalized = AnalysisNormalizationService().normalize_result(
        result,
        section_text,
        support_language=profile.support_language,
        target_level=profile.target_level,
    )
    normalized.quality_warnings = [
        warning
        for warning in normalized.quality_warnings
        if not warning.startswith("section:") and "Full-document staged analysis is not implemented yet" not in warning
    ]
    normalized.quality_warnings.append(f"section:{section_index + 1}/{section_count}")
    return normalized


@router.post("/{document_id}/staged-analysis", response_model=StagedAnalysisResponse)
async def analyze_next_document_sections(
    document_id: str,
    payload: StagedAnalysisRequest | None = None,
    db: Session = Depends(get_db),
):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    payload = payload or StagedAnalysisRequest()
    readable_text = AcademicTextService().readable_section(document.content)
    sections = DocumentSectionService().split(readable_text)
    analysis_repository = AnalysisRepository(db)
    section_repository = SectionAnalysisRepository(db)
    analyzed_indices = set(section_repository.list_indices(document_id))
    if analysis_repository.get_result(document_id):
        analyzed_indices.add(0)
    candidate_indices = [index for index in range(len(sections)) if index not in analyzed_indices][: payload.max_sections]
    if not candidate_indices:
        return StagedAnalysisResponse(
            document_id=document_id,
            total_sections=len(sections),
            skipped_sections=sorted(index + 1 for index in analyzed_indices),
            status="nothing_to_do",
            message="All available sections are already analyzed.",
        )

    service = AnalysisPipelineService(DocumentRepository(db), analysis_repository, section_repository)
    profile = UserProfileRepository(db).get_or_create()
    completed: list[int] = []
    for index in candidate_indices:
        try:
            result = await service.analyze_section(
                document_id,
                index,
                target_level=profile.target_level,
                support_language=profile.support_language,
                learning_language=profile.learning_language,
            )
        except RuntimeError as exc:
            if not completed:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
            return StagedAnalysisResponse(
                document_id=document_id,
                total_sections=len(sections),
                requested_sections=[item + 1 for item in candidate_indices],
                analyzed_sections=completed,
                skipped_sections=sorted(item + 1 for item in analyzed_indices),
                status="partial",
                message=f"Stopped after {len(completed)} sections: {exc}",
            )
        if not result:
            break
        completed.append(index + 1)

    return StagedAnalysisResponse(
        document_id=document_id,
        total_sections=len(sections),
        requested_sections=[item + 1 for item in candidate_indices],
        analyzed_sections=completed,
        skipped_sections=sorted(item + 1 for item in analyzed_indices),
        status="completed" if len(completed) == len(candidate_indices) else "partial",
        message=f"Analyzed {len(completed)} section(s).",
    )


@router.post("/{document_id}/page-batches", response_model=PageBatchAnalysisResponse)
async def analyze_next_document_pages(
    document_id: str,
    payload: PageBatchAnalysisRequest | None = None,
    db: Session = Depends(get_db),
):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    payload = payload or PageBatchAnalysisRequest()
    readable_text = AcademicTextService().readable_section(document.content)
    sections = DocumentSectionService().split_with_labels(readable_text)
    pages = _learning_pages(sections)
    section_repository = SectionAnalysisRepository(db)
    analyzed_indices = set(section_repository.list_indices(document_id))
    if AnalysisRepository(db).get_result(document_id):
        analyzed_indices.add(0)

    page_to_indices = _page_to_section_indices(sections)
    candidate_pages = [
        page
        for page in pages
        if any(index not in analyzed_indices for index in page_to_indices.get(page, []))
    ][: payload.max_pages]
    if not candidate_pages:
        return PageBatchAnalysisResponse(
            document_id=document_id,
            total_pages=len(pages),
            total_sections=len(sections),
            skipped_sections=sorted(index + 1 for index in analyzed_indices),
            status="nothing_to_do",
            message="All available pages are already prepared.",
        )

    service = AnalysisPipelineService(DocumentRepository(db), AnalysisRepository(db), section_repository)
    profile = UserProfileRepository(db).get_or_create()
    analyzed_pages: list[int] = []
    analyzed_sections: list[int] = []
    for page in candidate_pages:
        try:
            results = await service.analyze_page_sections(
                document_id,
                page,
                target_level=profile.target_level,
                support_language=profile.support_language,
                learning_language=profile.learning_language,
            )
        except RuntimeError as exc:
            if not analyzed_pages:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
            return PageBatchAnalysisResponse(
                document_id=document_id,
                total_pages=len(pages),
                total_sections=len(sections),
                requested_pages=candidate_pages,
                analyzed_pages=analyzed_pages,
                analyzed_sections=analyzed_sections,
                skipped_sections=sorted(index + 1 for index in analyzed_indices),
                status="partial",
                message=f"Stopped after {len(analyzed_pages)} page(s): {exc}",
            )
        if results is None:
            break
        analyzed_pages.append(page)
        analyzed_sections.extend(index + 1 for index, _ in results)

    return PageBatchAnalysisResponse(
        document_id=document_id,
        total_pages=len(pages),
        total_sections=len(sections),
        requested_pages=candidate_pages,
        analyzed_pages=analyzed_pages,
        analyzed_sections=analyzed_sections,
        skipped_sections=sorted(index + 1 for index in analyzed_indices),
        status="completed" if len(analyzed_pages) == len(candidate_pages) else "partial",
        message=f"Prepared {len(analyzed_pages)} page(s) with {len(analyzed_sections)} section lesson(s).",
    )


@router.get("/{document_id}/analysis", response_model=AnalysisResult)
def get_analysis(document_id: str, db: Session = Depends(get_db)):
    result = AnalysisRepository(db).get_result(document_id)
    if not result:
        raise not_found("Analysis not found")
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    readable_text = AcademicTextService().readable_section(document.content)
    settings = get_settings()
    analysis_text = " ".join(readable_text.split())
    if len(analysis_text) > settings.analysis_model_input_chars:
        analysis_text = analysis_text[: settings.analysis_model_input_chars].rsplit(" ", 1)[0]
    profile = UserProfileRepository(db).get_or_create()
    normalized = AnalysisNormalizationService().normalize_result(
        result,
        analysis_text,
        support_language=profile.support_language,
        target_level=profile.target_level,
    )
    return normalized


@router.get("/{document_id}/paper-map", response_model=PaperMapResponse)
def get_paper_map(document_id: str, db: Session = Depends(get_db)):
    document = DocumentRepository(db).get(document_id)
    if not document:
        raise not_found("Document not found")
    readable_text = AcademicTextService().readable_section(document.content)
    sections = DocumentSectionService().split(readable_text)
    profile = UserProfileRepository(db).get_or_create()
    return PaperMapService(AnalysisRepository(db), SectionAnalysisRepository(db)).build(
        document_id,
        sections,
        support_language=profile.support_language,
        target_level=profile.target_level,
    )


def _learning_pages(sections) -> list[int]:
    pages = sorted({page for page in (_page_number(section.source_label, index) for index, section in enumerate(sections)) if page is not None})
    return pages


def _page_to_section_indices(sections) -> dict[int, list[int]]:
    pages: dict[int, list[int]] = {}
    for index, section in enumerate(sections):
        page = _page_number(section.source_label, index)
        if page is None:
            continue
        pages.setdefault(page, []).append(index)
    return pages


def _page_number(label: str | None, index: int) -> int | None:
    if not label and index == 0:
        return 1
    if not label:
        return None
    if not label.startswith("PDF page "):
        return None
    try:
        return int(label.removeprefix("PDF page "))
    except ValueError:
        return None
