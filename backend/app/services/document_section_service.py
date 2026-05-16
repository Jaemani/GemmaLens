import re
from dataclasses import dataclass

from app.services.text_cleanup_service import normalize_pdf_ligatures


@dataclass(frozen=True)
class DocumentSection:
    text: str
    source_label: str | None = None


class DocumentSectionService:
    section_chars = 1800
    page_marker_pattern = re.compile(r"\[\[GEMMALENS_PDF_PAGE:(\d+)]]")

    def split(self, text: str) -> list[str]:
        return [section.text for section in self.split_with_labels(text)]

    def split_with_labels(self, text: str) -> list[DocumentSection]:
        if not self.page_marker_pattern.search(text):
            return self._merge_dangling_sections(
                [DocumentSection(section) for section in self._split_plain(self._clean(text)) if self._is_learning_section(section)]
            )

        sections: list[DocumentSection] = []
        parts = self.page_marker_pattern.split(text)
        leading = parts[0]
        sections.extend(DocumentSection(section) for section in self._split_plain(self._clean(leading)) if self._is_learning_section(section))
        for index in range(1, len(parts), 2):
            page_number = parts[index]
            page_text = parts[index + 1] if index + 1 < len(parts) else ""
            label = f"PDF page {page_number}"
            sections.extend(DocumentSection(section, label) for section in self._split_plain(self._clean(page_text)) if self._is_learning_section(section))
        return self._merge_dangling_sections(sections)

    def _split_plain(self, cleaned: str) -> list[str]:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip() and self._is_learning_section(part)]
        sections: list[str] = []
        current = ""
        for sentence in sentences:
            if current and len(current) + len(sentence) > self.section_chars:
                sections.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            sections.append(current.strip())
        return sections

    def section(self, text: str, index: int) -> tuple[str, int] | None:
        sections = self.split(text)
        if index < 0 or index >= len(sections):
            return None
        return sections[index], len(sections)

    def _clean(self, text: str) -> str:
        text = normalize_pdf_ligatures(text)
        text = text.replace("\r\n", "\n")
        text = re.sub(r"([A-Za-z]{2,})-\s+\d+\s+([a-z]{2,})", r"\1\2", text)
        text = re.sub(r"([A-Za-z]{2,})-\s+([a-z]{2,})", r"\1\2", text)
        text = re.sub(r"([A-Za-z]{2,})-\s*\n\s*([a-z]{2,})", r"\1\2", text)
        text = re.sub(
            r"\b(?:tion|sion|ment|sentation|resentation|pre)\s+(?:model|models|network|networks|training|representations)\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _merge_dangling_sections(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        merged: list[DocumentSection] = []
        index = 0
        while index < len(sections):
            current = sections[index]
            if index + 1 < len(sections) and self._is_dangling_section(current.text):
                following = sections[index + 1]
                merged.append(DocumentSection(self._clean(f"{current.text} {following.text}"), current.source_label or following.source_label))
                index += 2
                continue
            merged.append(current)
            index += 1
        return merged

    def _is_dangling_section(self, text: str) -> bool:
        normalized = " ".join(text.split())
        if len(normalized) > 350:
            return False
        return bool(re.search(r"[A-Za-z]{2,}-\s*\d*$", normalized))

    def _is_learning_section(self, text: str) -> bool:
        lowered = " ".join(text.lower().split())
        if not lowered:
            return False
        if len(lowered) < 80 and self._is_short_artifact(lowered):
            return False
        non_content_markers = [
            "work performed while",
            "conference on neural information processing systems",
            "spent countless long days",
            "initial codebase",
            "tensor2tensor",
            "provided proper attribution",
        ]
        if any(marker in lowered for marker in non_content_markers):
            return False
        return True

    def _is_short_artifact(self, lowered: str) -> bool:
        artifact_markers = [
            "weighted sum",
            "figure",
            "table",
            "equation",
            "where",
        ]
        return any(marker in lowered for marker in artifact_markers)
