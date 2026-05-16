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


class FakeSectionAnalysisRepositoryWithRows:
    def __init__(self, rows):
        self.rows = rows

    def list_results(self, document_id: str):
        return self.rows


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
    assert paper_map.synthesis.status == "whole-paper draft"
    assert paper_map.synthesis.priority_terms


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
    assert paper_map.synthesis.status == "partial synthesis"
    assert paper_map.synthesis.argument_flow
    assert any("Concept path" in item for item in paper_map.guide.reading_focus)
    assert any("next unstudied section" in item for item in paper_map.guide.next_steps)


def test_paper_map_includes_base_analysis_with_section_cache():
    text_one = "We introduce BERT, a bidirectional representation model."
    text_three = "The contributions of our paper include masked language modeling."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-3",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [{"term": "BERT", "meaning": "representation model", "domain_relevance": "high", "difficulty": "hard", "source_sentence": text_one, "should_save": True}],
            "phrases": [],
            "concepts": [{"concept": "BERT", "explanation": "main model", "source_sentence": text_one}],
            "sentences": [],
            "summaries": {"one_line": "The first section introduces BERT.", "simple": "The first section introduces BERT.", "academic": "The first section introduces BERT.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    section_three = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "terms": [
                {
                    "term": "masked language model",
                    "meaning": "pre-training objective",
                    "domain_relevance": "high",
                    "difficulty": "hard",
                    "source_sentence": text_three,
                    "should_save": True,
                }
            ],
            "concepts": [{"concept": "masked language model", "explanation": "pre-training objective", "source_sentence": text_three}],
            "summaries": {"one_line": "The third section lists contributions.", "simple": "The third section lists contributions.", "academic": "The third section lists contributions.", "study_notes": []},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(2, section_three)])).build(
        "doc-3", [text_one, "middle", text_three]
    )

    assert paper_map.analyzed_sections == [1, 3]
    assert [summary.text for summary in paper_map.section_summaries] == ["Section 1", "Section 3"]


def test_paper_map_skips_cached_attribution_sections():
    attribution = "Llion also experimented with novel model variants and was responsible for our initial codebase."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-4",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [{"term": "Transformer", "meaning": "attention model", "domain_relevance": "high", "difficulty": "hard", "source_sentence": "The Transformer uses attention.", "should_save": True}],
            "phrases": [],
            "concepts": [{"concept": "Transformer", "explanation": "attention model", "source_sentence": "The Transformer uses attention."}],
            "sentences": [],
            "summaries": {
                "one_line": "The first section introduces the Transformer.",
                "simple": "The first section introduces the Transformer.",
                "academic": "The first section introduces the Transformer.",
                "study_notes": [],
            },
            "quality_warnings": [],
        }
    )
    bad_cached = base.model_copy(
        update={"summaries": base.summaries.model_copy(update={"one_line": attribution, "simple": attribution, "academic": attribution})}
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(1, bad_cached)])).build(
        "doc-4", ["The Transformer uses attention.", attribution]
    )

    assert paper_map.analyzed_sections == [1]
    assert [summary.text for summary in paper_map.section_summaries] == ["Section 1"]


def test_paper_map_argument_flow_groups_duplicates_and_trims_long_entries():
    repeated = "The paper introduces the Transformer, an attention-only architecture for sequence transduction."
    long_summary = (
        "This section explains recurrent sequence-modeling baselines before the Transformer contrast, including long short-term memory, "
        "gated recurrent neural networks, language modeling, machine translation, sequential computation, and dependency paths."
    )
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-5",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [{"term": "Transformer", "meaning": "attention model", "domain_relevance": "high", "difficulty": "hard", "source_sentence": "The Transformer uses attention.", "should_save": True}],
            "phrases": [],
            "concepts": [{"concept": "Transformer", "explanation": "attention model", "source_sentence": "The Transformer uses attention."}],
            "sentences": [],
            "summaries": {"one_line": repeated, "simple": f"{repeated} Simple.", "academic": f"{repeated} Academic.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    repeated_section = base.model_copy()
    long_section = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "summaries": {"one_line": long_summary, "simple": f"{long_summary} Simple.", "academic": f"{long_summary} Academic.", "study_notes": []},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(1, repeated_section), (2, long_section)])).build(
        "doc-5", ["one", "two", "three"]
    )

    assert paper_map.synthesis.argument_flow[0].startswith("S1, 2:")
    assert len(paper_map.synthesis.argument_flow) == 2
    assert len(paper_map.synthesis.argument_flow[1]) < 190
