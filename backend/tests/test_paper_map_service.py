from app.schemas.analysis_schema import AnalysisResult
from app.services.paper_map_service import PaperMapService


class FakeAnalysisRepository:
    def __init__(self, result):
        self.result = result

    def get_result(self, document_id: str):
        return self.result


class FakeSectionAnalysisRepository:
    def list_results(self, document_id: str):
        return []


def test_paper_map_normalizes_base_analysis_when_no_section_cache():
    text = (
        "Training Deep Neural Networks is complicated by the fact that the distribution "
        "of each layer's inputs changes during training. Batch Normalization reduces "
        "internal covariate shift."
    )
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-1",
            "domain": {
                "primary_domain": "Machine Learning",
                "secondary_domains": [],
                "document_type": "paper",
                "confidence": 0.5,
            },
            "difficulty": {
                "overall_level": "C2",
                "lexical_difficulty": 5,
                "syntax_difficulty": 5,
                "domain_difficulty": 6,
                "reason": "test",
            },
            "terms": [
                {
                    "term": "Training Deep Neural Networks",
                    "meaning": "generic fragment",
                    "domain_relevance": "high",
                    "difficulty": "medium",
                    "source_sentence": text,
                    "should_save": True,
                }
            ],
            "phrases": [],
            "concepts": [
                {
                    "concept": "inputs changes during training",
                    "explanation": "generic fragment",
                    "source_sentence": text,
                }
            ],
            "sentences": [],
            "summaries": {"one_line": text, "simple": text, "academic": text, "study_notes": []},
            "quality_warnings": [],
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepository()).build("doc-1", [text])
    mapped = {item.text.lower() for item in [*paper_map.top_concepts, *paper_map.top_terms]}

    assert "training deep neural networks" not in mapped
    assert "inputs changes during training" not in mapped
    assert "batch normalization" in mapped
    assert paper_map.guide.coverage_note == "1 of 1 sections analyzed. This is a partial reading guide, not a whole-paper conclusion."
    assert paper_map.guide.reading_focus


def test_paper_map_guide_separates_partial_coverage_from_whole_paper_claim():
    text = (
        "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms. "
        "Self-attention allows the model to draw global dependencies and improve sequence transduction."
    )
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-2",
            "domain": {
                "primary_domain": "Machine Learning",
                "secondary_domains": [],
                "document_type": "paper",
                "confidence": 0.5,
            },
            "difficulty": {
                "overall_level": "C2",
                "lexical_difficulty": 6,
                "syntax_difficulty": 6,
                "domain_difficulty": 8,
                "reason": "test",
            },
            "terms": [
                {
                    "term": "Transformer",
                    "meaning": "attention-only architecture",
                    "domain_relevance": "high",
                    "difficulty": "hard",
                    "source_sentence": text,
                    "should_save": True,
                }
            ],
            "phrases": [{"phrase": "based solely on", "function": "method", "explanation": "states the design choice", "source_sentence": text}],
            "concepts": [{"concept": "self-attention", "explanation": "connects sequence positions", "source_sentence": text}],
            "sentences": [],
            "summaries": {
                "one_line": "The section introduces the Transformer as an attention-only architecture.",
                "simple": "The section introduces the Transformer as an attention-only architecture.",
                "academic": "The section introduces the Transformer as an attention-only architecture.",
                "study_notes": [],
            },
            "quality_warnings": [],
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepository()).build("doc-2", [text, "Future section text"])

    assert paper_map.guide.thesis_so_far.startswith("So far")
    assert "1 of 2 sections analyzed" in paper_map.guide.coverage_note
    assert any("Concept path" in item for item in paper_map.guide.reading_focus)
    assert any("next unstudied section" in item for item in paper_map.guide.next_steps)
