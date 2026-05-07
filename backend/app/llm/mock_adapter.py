from app.llm.base import ModelAdapter
from app.schemas.analysis_schema import (
    AnalysisResult,
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
    async def analyze_document(self, document_id: str, text: str, chunks: list[str]) -> AnalysisResult:
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
                TermItem(term="sleep deprivation", meaning="a state of not getting enough sleep", domain_relevance="high", difficulty="medium", source_sentence=first_sentence),
                TermItem(term="cognitive performance", meaning="how well the mind performs tasks like memory, attention, and reasoning", domain_relevance="high", difficulty="medium", source_sentence=first_sentence),
                TermItem(term="generalize", meaning="apply findings from one context to other contexts", domain_relevance="medium", difficulty="hard", source_sentence=first_sentence),
                TermItem(term="real-world learning environments", meaning="actual educational settings outside controlled experiments", domain_relevance="high", difficulty="hard", source_sentence=first_sentence),
                TermItem(term="longitudinal study", meaning="research that observes the same subjects over time", domain_relevance="high", difficulty="hard", source_sentence=second_sentence),
            ],
            phrases=[
                PhraseItem(phrase="previous studies have suggested", function="claim", explanation="Introduces existing evidence without making a fully certain claim.", source_sentence=first_sentence),
                PhraseItem(phrase="the extent to which", function="general", explanation="Frames a question about degree or scope.", source_sentence=first_sentence),
                PhraseItem(phrase="remains unclear", function="limitation", explanation="Marks an unresolved research problem.", source_sentence=first_sentence),
                PhraseItem(phrase="to address this gap", function="method", explanation="Connects the research gap to the authors' method.", source_sentence=second_sentence),
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
