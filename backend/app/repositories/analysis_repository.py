import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.schemas.analysis_schema import AnalysisResult


class AnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, result: AnalysisResult) -> Analysis:
        existing = self.get_model(result.document_id)
        payload = result.model_dump_json()
        if existing:
            existing.payload = payload
            self.db.commit()
            self.db.refresh(existing)
            return existing
        analysis = Analysis(document_id=result.document_id, payload=payload)
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_model(self, document_id: str) -> Analysis | None:
        return self.db.scalar(select(Analysis).where(Analysis.document_id == document_id))

    def get_result(self, document_id: str) -> AnalysisResult | None:
        model = self.get_model(document_id)
        if not model:
            return None
        return AnalysisResult.model_validate(json.loads(model.payload))
