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
    assert paper_map.guide.coverage_note == "1 of 1 sections analyzed. This is a complete section-level reading guide."
    assert paper_map.guide.reading_focus
    assert paper_map.synthesis.status == "complete section guide"
    assert paper_map.synthesis.priority_terms


def _paper_result(summary: str, concept: str = "residual learning framework") -> AnalysisResult:
    text = f"{summary} {concept}"
    return AnalysisResult.model_validate(
        {
            "document_id": "doc-complete",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [{"term": concept, "meaning": "paper concept", "domain_relevance": "high", "difficulty": "hard", "source_sentence": text, "should_save": True}],
            "phrases": [{"phrase": "We show that", "function": "result", "explanation": "result signal", "source_sentence": "We show that."}],
            "concepts": [{"concept": concept, "explanation": "paper concept", "source_sentence": text}],
            "sentences": [],
            "summaries": {"one_line": summary, "simple": summary, "academic": summary, "study_notes": []},
            "quality_warnings": [],
        }
    )


def test_complete_paper_map_keeps_all_section_summaries_and_complete_copy():
    section_texts = [f"Section {index} text." for index in range(1, 29)]
    base = _paper_result("Section 1 summary.")
    rows = [(index, _paper_result(f"Section {index + 1} summary.")) for index in range(1, 28)]

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows(rows)).build("doc-complete", section_texts)

    assert paper_map.analyzed_sections == list(range(1, 29))
    assert paper_map.guide.coverage_note == "28 of 28 sections analyzed. This is a complete section-level reading guide."
    assert paper_map.guide.thesis_so_far.startswith("Across the paper")
    assert not any("Latest section signal" in item for item in paper_map.guide.reading_focus)
    assert any("Whole-paper path" in item for item in paper_map.guide.reading_focus)
    assert "Analyze the next unstudied section" not in " ".join(paper_map.guide.next_steps)
    assert len(paper_map.section_summaries) == 28
    assert paper_map.section_summaries[-1].text == "Section 28"
    assert any(item.startswith("S28:") for item in paper_map.synthesis.argument_flow)
    assert not any("more analyzed section summaries" in item for item in paper_map.synthesis.argument_flow)


def test_paper_map_argument_flow_skips_reference_boundary_artifacts():
    section_texts = [
        "The paper introduces a useful training method.",
        "This section closes the conclusion, then starts the references.",
        "This appendix explains the implementation details.",
    ]
    base = _paper_result("The paper introduces a useful training method.", "training method")
    rows = [
        (1, _paper_result("This is a reference-list section, so it should be skimmed for cited sources rather than studied as prose.", "references")),
        (2, _paper_result("This appendix explains the implementation details.", "implementation details")),
    ]

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows(rows)).build("doc-complete", section_texts)
    flow_text = " ".join(paper_map.synthesis.argument_flow).lower()

    assert "reference-list section" not in flow_text
    assert "implementation details" in flow_text


def test_paper_map_priority_lists_skip_study_noise():
    text = "BERT uses masked language modeling for bidirectional pre-training."
    result = AnalysisResult.model_validate(
        {
            "document_id": "doc-biblio",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [
                {"term": "BERT", "meaning": "language representation model", "domain_relevance": "high", "difficulty": "hard", "source_sentence": text, "should_save": True},
                {"term": "ACL", "meaning": "conference metadata", "domain_relevance": "low", "difficulty": "easy", "source_sentence": text, "should_save": False},
                {
                    "term": "Advances in neural information processing systems",
                    "meaning": "conference metadata",
                    "domain_relevance": "low",
                    "difficulty": "easy",
                    "source_sentence": text,
                    "should_save": False,
                },
                {"term": "Proceedings", "meaning": "venue metadata", "domain_relevance": "low", "difficulty": "easy", "source_sentence": text, "should_save": False},
                {"term": "arXiv preprint", "meaning": "bibliography metadata", "domain_relevance": "low", "difficulty": "easy", "source_sentence": text, "should_save": False},
            ],
            "phrases": [
                {"phrase": "In ACL", "function": "general", "explanation": "conference marker", "source_sentence": text},
                {"phrase": "In CoNLL", "function": "general", "explanation": "conference marker", "source_sentence": text},
                {"phrase": "In Proceedings of", "function": "general", "explanation": "bibliography marker", "source_sentence": text},
                {"phrase": "50% of the time", "function": "general", "explanation": "sampling ratio", "source_sentence": text},
                {"phrase": "is a collection of", "function": "general", "explanation": "generic definition fragment", "source_sentence": text},
                {"phrase": "In contrast to", "function": "contrast", "explanation": "contrast signal", "source_sentence": text},
            ],
            "concepts": [{"concept": "masked language model", "explanation": "paper concept", "source_sentence": text}],
            "sentences": [],
            "summaries": {"one_line": text, "simple": text, "academic": text, "study_notes": []},
            "quality_warnings": [],
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(result), FakeSectionAnalysisRepository()).build("doc-biblio", [text])
    top_text = {item.text.lower() for item in [*paper_map.synthesis.priority_terms, *paper_map.synthesis.reusable_expressions]}

    assert "bert" in top_text
    assert "acl" not in top_text
    assert "advances in neural information processing systems" not in top_text
    assert "in acl" not in top_text
    assert "in conll" not in top_text
    assert "proceedings" not in top_text
    assert "arxiv preprint" not in top_text
    assert "in proceedings of" not in top_text
    assert "50% of the time" not in top_text
    assert "is a collection of" not in top_text


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


def test_paper_map_skips_short_cached_formula_fragments():
    text = "Scaled Dot-Product Attention uses queries, keys, and values to compute attention weights."
    fragment = "The output is computed as a weighted sum 3"
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-6",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [{"term": "scaled dot-product attention", "meaning": "attention mechanism", "domain_relevance": "high", "difficulty": "hard", "source_sentence": text, "should_save": True}],
            "phrases": [],
            "concepts": [{"concept": "scaled dot-product attention", "explanation": "attention mechanism", "source_sentence": text}],
            "sentences": [],
            "summaries": {"one_line": text, "simple": text, "academic": text, "study_notes": []},
            "quality_warnings": [],
        }
    )
    bad_cached = base.model_copy(
        update={"summaries": base.summaries.model_copy(update={"one_line": fragment, "simple": fragment, "academic": fragment})}
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(1, bad_cached)])).build(
        "doc-6", [text, fragment]
    )

    assert paper_map.analyzed_sections == [1]
    assert all("weighted sum 3" not in summary.meaning for summary in paper_map.section_summaries)


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


def test_paper_map_argument_flow_does_not_hide_seventh_section():
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-flow",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "Section 1 explains the opening claim.", "simple": "Section 1.", "academic": "Section 1.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    sections = [
        (
            index,
            base.model_copy(
                update={
                    "summaries": base.summaries.model_copy(
                        update={"one_line": f"Section {index + 2} explains a distinct learning step."}
                    )
                }
            ),
        )
        for index in range(1, 7)
    ]

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows(sections)).build(
        "doc-flow", [f"section {index}" for index in range(7)]
    )

    assert len(paper_map.synthesis.argument_flow) == 7
    assert paper_map.synthesis.argument_flow[-1].startswith("S7:")
    assert not any("more analyzed section summaries" in item for item in paper_map.synthesis.argument_flow)


def test_paper_map_argument_flow_does_not_hide_tenth_section():
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-flow-10",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "Section 1 explains the opening claim.", "simple": "Section 1.", "academic": "Section 1.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    sections = [
        (
            index,
            base.model_copy(
                update={
                    "summaries": base.summaries.model_copy(
                        update={"one_line": f"Section {index + 2} explains a distinct learning step."}
                    )
                }
            ),
        )
        for index in range(1, 10)
    ]

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows(sections)).build(
        "doc-flow-10", [f"section {index}" for index in range(10)]
    )

    assert len(paper_map.synthesis.argument_flow) == 10
    assert paper_map.synthesis.argument_flow[-1].startswith("S10:")
    assert not any("more analyzed section summaries" in item for item in paper_map.synthesis.argument_flow)


def test_paper_map_argument_flow_keeps_latest_section_when_longer_than_limit():
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-flow-latest",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "Section 1 explains the opening claim.", "simple": "Section 1.", "academic": "Section 1.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    sections = [
        (
            index,
            base.model_copy(
                update={
                    "summaries": base.summaries.model_copy(
                        update={"one_line": f"Section {index + 2} explains a distinct learning step."}
                    )
                }
            ),
        )
        for index in range(1, 21)
    ]

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows(sections)).build(
        "doc-flow-latest", [f"section {index}" for index in range(22)]
    )

    assert any(item.startswith("S21:") for item in paper_map.synthesis.argument_flow)
    assert any("more analyzed section summaries" in item for item in paper_map.synthesis.argument_flow)


def test_paper_map_argument_flow_shows_twenty_section_reading_path():
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-flow-20",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "Section 1 explains the opening claim.", "simple": "Section 1.", "academic": "Section 1.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    sections = [
        (
            index,
            base.model_copy(
                update={
                    "summaries": base.summaries.model_copy(
                        update={"one_line": f"Section {index + 2} explains a distinct learning step."}
                    )
                }
            ),
        )
        for index in range(1, 20)
    ]

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows(sections)).build(
        "doc-flow-20", [f"section {index}" for index in range(20)]
    )

    assert len(paper_map.synthesis.argument_flow) == 20
    assert paper_map.synthesis.argument_flow[-1].startswith("S20:")
    assert not any("more analyzed section summaries" in item for item in paper_map.synthesis.argument_flow)


def test_paper_map_ranks_core_methods_before_generic_descriptors():
    text = "We present a residual learning framework for deeper neural networks and learning residual functions."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-7",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [
                {"term": "deeper neural networks", "meaning": "generic descriptor", "domain_relevance": "high", "difficulty": "hard", "source_sentence": text, "should_save": True},
                {"term": "residual learning framework", "meaning": "main method", "domain_relevance": "high", "difficulty": "hard", "source_sentence": text, "should_save": True},
                {"term": "residual functions", "meaning": "learning target", "domain_relevance": "high", "difficulty": "hard", "source_sentence": text, "should_save": True},
            ],
            "phrases": [],
            "concepts": [
                {"concept": "deeper neural networks", "explanation": "generic descriptor", "source_sentence": text},
                {"concept": "residual learning framework", "explanation": "main method", "source_sentence": text},
                {"concept": "residual functions", "explanation": "learning target", "source_sentence": text},
            ],
            "sentences": [],
            "summaries": {"one_line": "The paper introduces residual learning.", "simple": "The paper introduces residual learning.", "academic": "The paper introduces residual learning.", "study_notes": []},
            "quality_warnings": [],
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepository()).build("doc-7", [text])

    assert [item.text for item in paper_map.synthesis.priority_concepts[:2]] == ["residual functions", "residual learning framework"]
    assert paper_map.synthesis.priority_concepts[2].text == "deeper neural networks"


def test_paper_map_priority_concepts_do_not_collapse_to_only_repeated_items():
    text_one = "We present a residual learning framework and residual functions."
    text_two = "A degradation problem leads to higher training error."
    text_three = "A constructed solution uses identity mapping to explain higher training error."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-8",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [],
            "concepts": [
                {"concept": "residual learning framework", "explanation": "main method", "source_sentence": text_one},
                {"concept": "residual functions", "explanation": "learning target", "source_sentence": text_one},
            ],
            "sentences": [],
            "summaries": {"one_line": "The paper introduces residual learning.", "simple": "The paper introduces residual learning.", "academic": "The paper introduces residual learning.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    section_two = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "concepts": [{"concept": "higher training error", "explanation": "optimization evidence", "source_sentence": text_two}],
            "summaries": {**base.summaries.model_dump(), "one_line": "The section motivates degradation through higher training error."},
        }
    )
    section_three = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "concepts": [
                {"concept": "higher training error", "explanation": "optimization evidence", "source_sentence": text_three},
                {"concept": "constructed solution", "explanation": "theoretical copy argument", "source_sentence": text_three},
            ],
            "summaries": {**base.summaries.model_dump(), "one_line": "The section explains the constructed solution argument."},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(1, section_two), (2, section_three)])).build(
        "doc-8", [text_one, text_two, text_three]
    )
    priority = [item.text for item in paper_map.synthesis.priority_concepts]

    assert priority[:2] == ["residual functions", "residual learning framework"]
    assert "higher training error" in priority
    assert len(priority) > 1


def test_paper_map_promotes_argument_expressions_over_early_generic_phrases():
    text_one = "We provide comprehensive empirical evidence showing that residual networks are easier to optimize."
    text_two = "Unexpectedly, such degradation is not caused by overfitting."
    text_three = "There exists a solution by construction to the deeper model."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-9",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [
                {
                    "phrase": "provide comprehensive empirical evidence",
                    "function": "result",
                    "explanation": "generic evidence signal",
                    "source_sentence": text_one,
                }
            ],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "The first section introduces evidence.", "simple": "The first section introduces evidence.", "academic": "The first section introduces evidence.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    section_two = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [{"phrase": "not caused by overfitting", "function": "contrast", "explanation": "rejects a common explanation", "source_sentence": text_two}],
            "summaries": {**base.summaries.model_dump(), "one_line": "The section rejects overfitting as the cause."},
        }
    )
    section_three = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [
                {
                    "phrase": "There exists a solution by construction",
                    "function": "claim",
                    "explanation": "theoretical existence argument",
                    "source_sentence": text_three,
                }
            ],
            "summaries": {**base.summaries.model_dump(), "one_line": "The section explains the constructed solution."},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(1, section_two), (2, section_three)])).build(
        "doc-9", [text_one, text_two, text_three]
    )
    expressions = [item.text for item in paper_map.synthesis.reusable_expressions]

    assert expressions[:2] == ["not caused by overfitting", "There exists a solution by construction"]


def test_paper_map_reusable_expressions_include_latest_section_signals():
    base_text = "Unexpectedly, such degradation is not caused by overfitting."
    latest_text = "Instead of hoping layers directly fit the target, the original mapping is recast into F(x)+x."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-10",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [{"phrase": "not caused by overfitting", "function": "contrast", "explanation": "rejects a cause", "source_sentence": base_text}],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "The section rejects overfitting.", "simple": "The section rejects overfitting.", "academic": "The section rejects overfitting.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    section_two = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [{"phrase": "There exists a solution by construction", "function": "claim", "explanation": "existence argument", "source_sentence": "There exists a solution by construction."}],
            "summaries": {**base.summaries.model_dump(), "one_line": "The section gives an existence argument."},
        }
    )
    section_three = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [
                {"phrase": "Instead of hoping", "function": "contrast", "explanation": "contrast learning targets", "source_sentence": latest_text},
                {"phrase": "is recast into", "function": "method", "explanation": "mathematical reformulation", "source_sentence": latest_text},
            ],
            "summaries": {**base.summaries.model_dump(), "one_line": "The section defines residual mapping."},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(1, section_two), (2, section_three)])).build(
        "doc-10", [base_text, "There exists a solution by construction.", latest_text]
    )
    expressions = [item.text for item in paper_map.synthesis.reusable_expressions]

    assert "Instead of hoping" in expressions
    assert "is recast into" in expressions


def test_paper_map_reusable_expression_candidates_keep_later_sections():
    base_text = "The early section says one generic result."
    latest_text = "We show that residual nets are easy to optimize, exhibit higher training error in plain nets, and accuracy gains from depth."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-11",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [
                {"phrase": f"early phrase {index}", "function": "result", "explanation": "early", "source_sentence": f"early phrase {index}"}
                for index in range(14)
            ],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "The first section gives early evidence.", "simple": "The first section gives early evidence.", "academic": "The first section gives early evidence.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    latest = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [
                {"phrase": "We show that", "function": "result", "explanation": "opens result list", "source_sentence": latest_text},
                {"phrase": "exhibit higher training error", "function": "result", "explanation": "states baseline failure", "source_sentence": latest_text},
            ],
            "summaries": {**base.summaries.model_dump(), "one_line": "The latest section states experiment claims."},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(4, latest)])).build(
        "doc-11", [base_text, "two", "three", "four", latest_text]
    )
    expressions = [item.text for item in paper_map.synthesis.reusable_expressions]

    assert "We show that" in expressions
    assert "exhibit higher training error" in expressions


def test_paper_map_promotes_resnet_result_expressions():
    latest_text = "We show that residual nets are easy to optimize, exhibit higher training error in plain nets, and accuracy gains from depth."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-12",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [
                {"phrase": "as easy as stacking more layers", "function": "limitation", "explanation": "old", "source_sentence": "as easy as stacking more layers"},
                {"phrase": "not caused by overfitting", "function": "contrast", "explanation": "old", "source_sentence": "not caused by overfitting"},
            ],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "The early section frames the problem.", "simple": "The early section frames the problem.", "academic": "The early section frames the problem.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    latest = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [
                {"phrase": "We show that", "function": "result", "explanation": "opens result list", "source_sentence": latest_text},
                {"phrase": "exhibit higher training error", "function": "result", "explanation": "baseline failure", "source_sentence": latest_text},
                {"phrase": "accuracy gains from", "function": "result", "explanation": "accuracy claim", "source_sentence": "accuracy gains from depth"},
            ],
            "summaries": {**base.summaries.model_dump(), "one_line": "The latest section states empirical claims."},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(4, latest)])).build(
        "doc-12", ["one", "two", "three", "four", latest_text]
    )
    expressions = [item.text for item in paper_map.synthesis.reusable_expressions]

    assert "We show that" in expressions
    assert "exhibit higher training error" in expressions
    assert "accuracy gains from" in expressions


def test_paper_map_promotes_related_work_expressions():
    latest_text = "These methods suggest that reformulation helps, in contrast to gated shortcuts."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-13",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [{"phrase": "as easy as stacking more layers", "function": "limitation", "explanation": "old", "source_sentence": "as easy as stacking more layers"}],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "The early section frames the problem.", "simple": "The early section frames the problem.", "academic": "The early section frames the problem.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    latest = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [
                {"phrase": "These methods suggest that", "function": "claim", "explanation": "related-work synthesis", "source_sentence": latest_text},
                {"phrase": "in contrast to", "function": "contrast", "explanation": "method contrast", "source_sentence": latest_text},
                {"phrase": "Concurrent with our work", "function": "general", "explanation": "contemporaneous related work", "source_sentence": "Concurrent with our work, highway networks appear."},
            ],
            "summaries": {**base.summaries.model_dump(), "one_line": "The latest section positions related work."},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(5, latest)])).build(
        "doc-13", ["one", "two", "three", "four", "five", latest_text]
    )
    expressions = [item.text for item in paper_map.synthesis.reusable_expressions]

    assert "These methods suggest that" in expressions
    assert "in contrast to" in expressions


def test_paper_map_reusable_expressions_include_highway_transition_signals():
    base_text = "Unexpectedly, such degradation is not caused by overfitting."
    latest_text = (
        "On the contrary, our formulation always learns residual functions. "
        "In addition, highway networks have not demonstrated accuracy gains."
    )
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-14",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [{"phrase": "not caused by overfitting", "function": "contrast", "explanation": "rejects a common explanation", "source_sentence": base_text}],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "The early section frames the problem.", "simple": "The early section frames the problem.", "academic": "The early section frames the problem.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    latest = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [
                {"phrase": "On the contrary", "function": "contrast", "explanation": "method contrast", "source_sentence": latest_text},
                {"phrase": "In addition", "function": "general", "explanation": "adds support", "source_sentence": latest_text},
                {"phrase": "Let us consider", "function": "general", "explanation": "opens formal setup", "source_sentence": "Let us consider H(x)."},
            ],
            "summaries": {**base.summaries.model_dump(), "one_line": "The latest section contrasts highway networks with ResNet shortcuts."},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(6, latest)])).build(
        "doc-14", ["one", "two", "three", "four", "five", "six", latest_text]
    )
    expressions = [item.text for item in paper_map.synthesis.reusable_expressions]

    assert "On the contrary" in expressions
    assert "In addition" in expressions


def test_paper_map_reusable_expressions_include_architecture_transition_signals():
    base_text = "Unexpectedly, such degradation is not caused by overfitting."
    latest_text = "The identity mapping is sufficient and only used when matching dimensions. To provide instances for discussion, we describe models."
    base = AnalysisResult.model_validate(
        {
            "document_id": "doc-15",
            "domain": {"primary_domain": "Machine Learning", "secondary_domains": [], "document_type": "paper", "confidence": 0.5},
            "difficulty": {"overall_level": "C2", "lexical_difficulty": 6, "syntax_difficulty": 6, "domain_difficulty": 8, "reason": "test"},
            "terms": [],
            "phrases": [{"phrase": "not caused by overfitting", "function": "contrast", "explanation": "rejects a common explanation", "source_sentence": base_text}],
            "concepts": [],
            "sentences": [],
            "summaries": {"one_line": "The early section frames the problem.", "simple": "The early section frames the problem.", "academic": "The early section frames the problem.", "study_notes": []},
            "quality_warnings": [],
        }
    )
    latest = AnalysisResult.model_validate(
        {
            **base.model_dump(),
            "phrases": [
                {"phrase": "identity mapping is sufficient", "function": "result", "explanation": "identity shortcut is enough", "source_sentence": latest_text},
                {"phrase": "only used when matching dimensions", "function": "method", "explanation": "limits projection shortcut", "source_sentence": latest_text},
                {"phrase": "To provide instances for discussion", "function": "general", "explanation": "moves to architecture examples", "source_sentence": latest_text},
            ],
            "summaries": {**base.summaries.model_dump(), "one_line": "The latest section introduces network architecture choices."},
        }
    )

    paper_map = PaperMapService(FakeAnalysisRepository(base), FakeSectionAnalysisRepositoryWithRows([(8, latest)])).build(
        "doc-15", ["one", "two", "three", "four", "five", "six", "seven", "eight", latest_text]
    )
    expressions = [item.text for item in paper_map.synthesis.reusable_expressions]

    assert "identity mapping is sufficient" in expressions
    assert "only used when matching dimensions" in expressions
