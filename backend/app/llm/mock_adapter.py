from app.llm.base import ModelAdapter
from app.schemas.analysis_schema import (
    AnalysisResult,
    ConceptItem,
    DifficultyInfo,
    DomainInfo,
    LayeredSummaries,
    PhraseItem,
    SentenceDecomposition,
    TermItem,
)

SAMPLE_PARAGRAPH = (
    "Although previous studies have suggested a correlation between sleep deprivation "
    "and reduced cognitive performance, the extent to which these findings generalize "
    "across real-world learning environments remains unclear. To address this gap, "
    "we analyze longitudinal study logs collected from undergraduate students over a "
    "six-week period."
)


class MockModelAdapter(ModelAdapter):
    async def analyze_document(
        self,
        document_id: str,
        text: str,
        chunks: list[str],
        support_language: str = "Korean",
        learning_language: str = "English",
        target_level: str | None = None,
    ) -> AnalysisResult:
        source = text.strip() or SAMPLE_PARAGRAPH
        first_sentence = source.split(".")[0].strip() + "."
        second_sentence = (
            "To address this gap, we analyze longitudinal study logs collected from "
            "undergraduate students over a six-week period."
        )
        return AnalysisResult(
            document_id=document_id,
            domain=DomainInfo(
                primary_domain="education",
                secondary_domains=["cognitive science"],
                document_type="paper",
                confidence=0.86,
            ),
            difficulty=DifficultyInfo(
                overall_level="C1",
                lexical_difficulty=7,
                syntax_difficulty=8,
                domain_difficulty=6,
                reason="Dense academic syntax combines concession, uncertainty, and method framing.",
            ),
            terms=[
                TermItem(term="sleep deprivation", meaning="a state of not getting enough sleep", support_language_meaning="수면이 충분하지 않은 상태", domain_relevance="high", difficulty="medium", source_sentence=first_sentence),
                TermItem(term="cognitive performance", meaning="how well the mind performs tasks like memory, attention, and reasoning", support_language_meaning="기억, 주의, 추론 같은 인지 과제를 얼마나 잘 수행하는지", domain_relevance="high", difficulty="medium", source_sentence=first_sentence),
                TermItem(term="generalize", meaning="apply findings from one context to other contexts", support_language_meaning="한 맥락의 결과를 다른 맥락에도 적용하다", domain_relevance="medium", difficulty="hard", source_sentence=first_sentence),
                TermItem(term="real-world learning environments", meaning="actual educational settings outside controlled experiments", support_language_meaning="통제 실험이 아닌 실제 학습 환경", domain_relevance="high", difficulty="hard", source_sentence=first_sentence),
                TermItem(term="longitudinal study", meaning="research that observes the same subjects over time", support_language_meaning="같은 대상을 오랜 기간 관찰하는 연구", domain_relevance="high", difficulty="hard", source_sentence=second_sentence),
            ],
            phrases=[
                PhraseItem(phrase="previous studies have suggested", function="claim", explanation="Introduces existing evidence without making a fully certain claim.", support_language_explanation="기존 연구가 시사한다고 조심스럽게 말할 때 쓰는 표현", source_sentence=first_sentence),
                PhraseItem(phrase="the extent to which", function="general", explanation="Frames a question about degree or scope.", support_language_explanation="어느 정도까지 그런지를 묻는 표현", source_sentence=first_sentence),
                PhraseItem(phrase="remains unclear", function="limitation", explanation="Marks an unresolved research problem.", support_language_explanation="아직 명확하지 않다는 연구 공백을 표시", source_sentence=first_sentence),
                PhraseItem(phrase="to address this gap", function="method", explanation="Connects the research gap to the authors' method.", support_language_explanation="앞의 공백을 해결하기 위해 방법을 제시할 때 사용", source_sentence=second_sentence),
            ],
            concepts=[
                ConceptItem(
                    concept="generalize across real-world learning environments",
                    explanation="The research problem is whether a finding from previous studies applies in real learning contexts.",
                    source_sentence=first_sentence,
                    related_terms=["generalize", "real-world learning environments", "cognitive performance"],
                    why_it_matters="This concept explains why the paper exists, not just which words are difficult.",
                    references=[],
                    confidence=0.86,
                ),
                ConceptItem(
                    concept="longitudinal study logs",
                    explanation="A method concept: repeated learning records are observed across time.",
                    source_sentence=second_sentence,
                    related_terms=["longitudinal study", "study logs"],
                    why_it_matters="Understanding the method helps the reader evaluate the paper's evidence.",
                    references=[],
                    confidence=0.82,
                ),
            ],
            sentences=[
                SentenceDecomposition(
                    sentence=first_sentence,
                    core_structure="Although A, B remains unclear.",
                    simplified_version="Past studies found a link, but we still do not know if it applies in real classrooms.",
                    korean_explanation="'Although' 절은 배경 연구를 양보로 제시하고, 주절은 아직 불명확한 점을 말합니다.",
                    difficulty_reason="Long noun phrases and embedded question structure make the main claim hard to locate.",
                ),
                SentenceDecomposition(
                    sentence=second_sentence,
                    core_structure="To address this gap, we analyze X collected from Y over Z.",
                    simplified_version="We study six weeks of logs from undergraduates to investigate the gap.",
                    korean_explanation="'To address this gap'은 연구 목적을 나타내고, 주절은 분석 대상을 설명합니다.",
                    difficulty_reason="Method phrase, passive reduced clause, and time expression are packed into one sentence.",
                ),
            ],
            summaries=LayeredSummaries(
                one_line="The text studies whether sleep-related cognitive findings apply to real learning settings.",
                simple="Researchers know sleep loss may reduce thinking performance, but they are testing whether that finding holds in real undergraduate learning data.",
                academic="The passage identifies a generalizability gap in sleep deprivation and cognitive performance research, then proposes longitudinal analysis of undergraduate study logs as the method.",
                study_notes=[
                    "Use 'remains unclear' to state a research gap.",
                    "Use 'to address this gap' to move from problem to method.",
                    "Look for the main clause after long 'Although' openings.",
                ],
            ),
        )
