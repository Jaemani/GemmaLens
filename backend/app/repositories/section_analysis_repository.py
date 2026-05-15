import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.section_analysis import SectionAnalysis
from app.schemas.analysis_schema import AnalysisResult


class SectionAnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, section_index: int, result: AnalysisResult) -> SectionAnalysis:
        existing = self.get_model(result.document_id, section_index)
        payload = result.model_dump_json()
        if existing:
            existing.payload = payload
            self.db.commit()
            self.db.refresh(existing)
            return existing
        section = SectionAnalysis(document_id=result.document_id, section_index=section_index, payload=payload)
        self.db.add(section)
        self.db.commit()
        self.db.refresh(section)
        return section

    def get_model(self, document_id: str, section_index: int) -> SectionAnalysis | None:
        return self.db.scalar(
            select(SectionAnalysis).where(
                SectionAnalysis.document_id == document_id,
                SectionAnalysis.section_index == section_index,
            )
        )

    def get_result(self, document_id: str, section_index: int) -> AnalysisResult | None:
        model = self.get_model(document_id, section_index)
        if not model:
            return None
        return AnalysisResult.model_validate(json.loads(model.payload))

    def list_results(self, document_id: str) -> list[tuple[int, AnalysisResult]]:
        rows = self.db.scalars(
            select(SectionAnalysis).where(SectionAnalysis.document_id == document_id).order_by(SectionAnalysis.section_index)
        ).all()
        return [(row.section_index, AnalysisResult.model_validate(json.loads(row.payload))) for row in rows]

    def list_indices(self, document_id: str) -> list[int]:
        return list(
            self.db.scalars(
                select(SectionAnalysis.section_index).where(SectionAnalysis.document_id == document_id).order_by(SectionAnalysis.section_index)
            ).all()
        )
