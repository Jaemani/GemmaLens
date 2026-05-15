import re


class DocumentSectionService:
    section_chars = 1800

    def split(self, text: str) -> list[str]:
        cleaned = self._clean(text)
        if not cleaned:
            return []
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
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
        text = text.replace("\r\n", "\n")
        text = re.sub(r"([A-Za-z]{3,})-\s+([a-z]{2,})", r"\1\2", text)
        text = re.sub(r"([A-Za-z]{3,})-\s*\n\s*([a-z]{2,})", r"\1\2", text)
        text = re.sub(
            r"\b(?:tion|sion|ment|sentation|resentation|pre)\s+(?:model|models|network|networks|training|representations)\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()
