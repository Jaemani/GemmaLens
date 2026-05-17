from pathlib import Path
import re

from app.services.analysis_normalization_service import AnalysisNormalizationService
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.document_section_service import DocumentSectionService


def _analyze(text: str, level: str = "C2"):
    return AnalysisNormalizationService().normalize_payload(
        {"terms": [], "phrases": [], "sentences": [], "summaries": {}},
        f"matrix-{level}",
        text,
        support_language="Korean",
        target_level=level,
    )


def test_ml_paper_attention_background_c2_outputs_learning_signal_not_incidental_names():
    text = (
        "2 Background The goal of reducing sequential computation also forms the foundation of the Extended Neural GPU, "
        "ByteNet and ConvS2S, all of which use convolutional neural networks as basic building block, computing hidden "
        "representations in parallel for all input and output positions. In these models, the number of operations required "
        "to relate signals from two arbitrary input or output positions grows in the distance between positions. "
        "This makes it more difficult to learn dependencies between distant positions."
    )

    result = _analyze(text, "C2")
    terms = {term.term for term in result.terms}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert {"sequential computation", "in parallel", "convolutional neural networks", "hidden representations"}.issubset(terms)
    assert not {"Extended Neural GPU", "ByteNet", "ConvS2S"} & terms
    assert {"forms the foundation of", "computing hidden representations in parallel"} & phrases
    assert "rhetorical move" in result.sentences[0].difficulty_reason


def test_medical_paper_b2_outputs_evidence_terms_and_reading_help():
    text = (
        "The randomized controlled trial reports a narrower confidence interval for the primary outcome. "
        "Adverse events remained elevated in the high-dose group, although the effect size was modest."
    )

    result = _analyze(text, "B2")
    terms = {term.term for term in result.terms}

    assert {"randomized controlled trial", "confidence interval", "adverse events"}.issubset(terms)
    assert "main clause first" in result.sentences[0].difficulty_reason
    assert all("새로 분석하면" not in term.support_language_meaning for term in result.terms)


def test_climate_report_c2_outputs_risk_policy_terms_and_report_language():
    text = (
        "Although short-term energy demand remains volatile, climate risk is likely to remain elevated in coastal regions. "
        "The report recommends adaptation measures in response to projected flooding and faster decarbonization to reduce greenhouse gas emissions."
    )

    result = _analyze(text, "C2")
    terms = {term.term for term in result.terms}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert {"climate risk", "adaptation measures", "decarbonization", "greenhouse gas emissions"}.issubset(terms)
    assert {"is likely to", "in response to"}.issubset(phrases)
    assert result.sentences[0].core_structure == "Although A, B remains C."


def test_economics_report_c1_outputs_macro_terms_and_cautious_claim_language():
    text = (
        "Inflation expectations remain elevated as the labor market tightens. "
        "The committee notes that monetary policy is associated with slower credit growth over the next quarter."
    )

    result = _analyze(text, "C1")
    terms = {term.term for term in result.terms}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert {"inflation expectations", "labor market", "monetary policy"}.issubset(terms)
    assert "is associated with" in phrases
    assert result.sentences[0].core_structure == "X is associated with Y, especially when Z."


def test_api_docs_b2_outputs_docs_terms_and_requirement_sentence():
    text = (
        "The API endpoint returns a paginated list of documents. "
        "The request payload must include an authentication token to access private projects. "
        "Set this parameter to true when using a pagination cursor, and check the rate limit before retrying."
    )

    result = _analyze(text, "B2")
    terms = {term.term for term in result.terms}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert {"API endpoint", "request payload", "authentication token", "pagination cursor", "rate limit"}.issubset(terms)
    assert {"returns a", "must include", "set this parameter to"}.issubset(phrases)
    assert result.sentences[0].core_structure == "The request/payload must include X to do Y."
    assert "main clause first" in result.sentences[0].difficulty_reason


def test_video_transcript_c2_outputs_scene_terms_and_procedural_language():
    text = (
        "Before we deploy the migration, we need to run an idempotent preflight check. "
        "Otherwise, stale metadata can propagate across worker nodes."
    )

    result = _analyze(text, "C2")
    terms = {term.term for term in result.terms}
    phrases = {phrase.phrase for phrase in result.phrases}

    assert {"idempotent preflight check", "stale metadata", "worker nodes"}.issubset(terms)
    assert {"before we", "otherwise", "can propagate across"}.issubset(phrases)
    assert result.sentences[0].core_structure == "Before we do A, we need to do B."
    assert "rhetorical move" in result.sentences[0].difficulty_reason


def test_same_source_changes_sentence_guidance_between_b2_and_c2():
    text = "The intervention is associated with lower readmission rates, especially when follow-up visits occur within seven days."

    b2 = _analyze(text, "B2")
    c2 = _analyze(text, "C2")

    assert b2.sentences[0].core_structure == c2.sentences[0].core_structure
    assert "main clause first" in b2.sentences[0].difficulty_reason
    assert "rhetorical move" in c2.sentences[0].difficulty_reason


def test_real_youtube_style_transcript_snippets_do_not_collapse_to_empty_results():
    snippets = {
        "ml": (
            "In the last chapter, you and I started to step through the internal workings of a transformer. "
            "This is one of the key pieces of technology inside large language models, and a lot of other tools in the modern wave of AI."
        ),
        "climate": (
            "Human activities from pollution to overpopulation are driving up the earth's temperature. "
            "The main cause is a phenomenon known as the greenhouse effect, gases in the atmosphere trapping heat."
        ),
        "economics": "Hi, I'm Jacob Clifford and I'm the host of Crash Course economics. Today we explain choices, scarce resources, and opportunity cost.",
        "medical": (
            "Considering that I have a cold right now, I can't imagine a more appropriate topic than a virus. "
            "Viruses carry genetic material inside a protein shell."
        ),
        "fastapi": (
            "Hello and welcome to the Fast API course. Fast API is a super fast Python web framework. "
            "It has automatic documentation for request and response models."
        ),
    }

    expected_terms = {
        "ml": {"Transformer", "large language models"},
        "climate": {"human activities", "earth's temperature", "greenhouse effect"},
        "economics": {"economics", "scarce resources", "opportunity cost"},
        "medical": {"virus", "genetic material", "protein shell"},
        "fastapi": {"fast api", "Python web framework", "automatic documentation"},
    }

    for name, text in snippets.items():
        for level in ("B1", "B2", "C1", "C2"):
            result = _analyze(text, level)
            terms = {term.term for term in result.terms}
            assert expected_terms[name] & terms
            assert result.sentences
            assert all("새로 분석하면" not in term.support_language_meaning for term in result.terms)


def test_actual_youtube_fallback_openings_are_useful_across_levels():
    snippets = {
        "climate": (
            "There’s the human lifetime, where we all live, and then there’s hundreds of years that contain full human lifetimes. "
            "Understanding climate change across all these timelines is tough. The Earth's climate has never changed this fast. "
            "Today, we know carbonic acid gas as carbon dioxide. So, Foote became one of the first scientists to make the link "
            "between carbon dioxide and atmospheric heating. It was one of the first experiments demonstrating the greenhouse effect. "
            "Specifically, gases like carbon dioxide, methane, and water vapor are known collectively as greenhouse gases."
        ),
        "economics": (
            "I'm Mr. Clifford and I'm a high school economics teacher and YouTuber and I'm going to focus on teaching you the theories "
            "and graphs of economics. Adriene Hill is going to focus on showing you the real world applications of economics. "
            "So let's start with the basics. What is economics?"
        ),
        "fastapi": (
            "FastAPI makes it quicker and easier to develop APIs with Python. FastAPI is a modern, fast and high-performance web framework "
            "for building APIs with Python. In this video, I will show you how to get started working with FastAPI. "
            "The only requirement is basic knowledge of Python. To install FastAPI, use the Python package manager pip."
        ),
    }

    expected_terms = {
        "climate": {"climate change", "carbon dioxide", "greenhouse gases", "greenhouse effect"},
        "economics": {"economics", "theories and graphs", "real world applications"},
        "fastapi": {"FastAPI", "APIs with Python", "web framework", "Python package manager", "pip"},
    }

    for name, text in snippets.items():
        for level in ("B1", "B2", "C1", "C2"):
            result = _analyze(text, level)
            terms = {term.term for term in result.terms}
            assert len(result.terms) >= 2
            assert len(result.phrases) >= 1
            assert result.sentences
            assert expected_terms[name] & terms
            assert all("새로 분석하면" not in term.support_language_meaning for term in result.terms)


def test_ml_youtube_opening_does_not_promote_incidental_climate_terms():
    text = (
        "In the last chapter, you and I started to step through the internal workings of a transformer, "
        "the key piece of technology inside large language models. Transformers first hit the scene in a paper called "
        "Attention is All You Need. The attention mechanism processes data by turning words into embeddings. "
        "One mole of carbon dioxide is only mentioned as an unrelated example."
    )

    result = _analyze(text, "C2")
    terms = {term.term for term in result.terms}

    assert {"attention mechanism", "large language models", "embeddings"}.issubset(terms)
    assert "carbon dioxide" not in terms


def test_eval_papers_all_extracted_sections_have_learning_signal_at_all_levels():
    papers = [
        Path("tmp/eval_papers/attention_is_all_you_need.pdf"),
        Path("tmp/eval_papers/batch_norm.pdf"),
        Path("tmp/eval_papers/bert.pdf"),
    ]
    ingestion = DocumentIngestionService()
    splitter = DocumentSectionService()
    normalizer = AnalysisNormalizationService()

    for paper in papers:
        text = ingestion.normalize_text(ingestion._extract_pdf(paper.read_bytes()))
        pages = {int(match.group(1)) for match in re.finditer(r"\[\[GEMMALENS_PDF_PAGE:(\d+)]]", text)}
        sections = splitter.split_with_labels(text)
        assert pages
        assert sections
        assert all(section.title for section in sections)

        weak = []
        for index, section in enumerate(sections, start=1):
            for level in ("B1", "B2", "C1", "C2"):
                result = normalizer.normalize_payload(
                    {"terms": [], "phrases": [], "sentences": [], "summaries": {}},
                    f"{paper.stem}-{index}-{level}",
                    section.text,
                    support_language="Korean",
                    target_level=level,
                )
                if len(result.terms) < 2 or len(result.phrases) < 1 or len(result.sentences) < 1:
                    weak.append((index, section.source_label, section.title, level, len(result.terms), len(result.phrases)))

        assert weak == []
