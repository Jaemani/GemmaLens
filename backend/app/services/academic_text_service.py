import re

from app.services.text_cleanup_service import normalize_pdf_ligatures


class AcademicTextService:
    page_marker_pattern = re.compile(r"\[\[GEMMALENS_PDF_PAGE:\d+]]")

    def readable_section(self, text: str) -> str:
        normalized_lines = self._clean_lines(text)
        abstract = self._after_abstract(normalized_lines)
        if abstract:
            return abstract
        return self._drop_obvious_front_matter(normalized_lines)

    def _clean_lines(self, text: str) -> str:
        text = normalize_pdf_ligatures(text)
        lines: list[str] = []
        for raw_line in text.replace("\r\n", "\n").splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue
            if re.search(r"\b[\w.+-]+@[\w.-]+\.\w+\b", line):
                continue
            if re.match(r"^arXiv:\S+", line, flags=re.IGNORECASE):
                continue
            if line.lower() in {"abstract", "introduction", "references"}:
                lines.append(line)
                continue
            lines.append(line)
        return "\n".join(lines)

    def _after_abstract(self, text: str) -> str:
        match = re.search(r"\bAbstract\b", text)
        if not match:
            return ""
        after = text[match.end() :]
        after = re.sub(r"^\s*[:.-]?\s*", "", after)
        page_markers = list(self.page_marker_pattern.finditer(text[: match.start()]))
        if page_markers:
            after = f"{page_markers[-1].group(0)}\n{after}"
        return self._normalize_for_model(after)

    def _drop_obvious_front_matter(self, text: str) -> str:
        lines = text.splitlines()
        start = 0
        for index, line in enumerate(lines[:20]):
            if self._looks_like_content(line):
                start = index
                break
        return self._normalize_for_model("\n".join(lines[start:]))

    def _looks_like_content(self, line: str) -> bool:
        lowered = line.lower()
        if any(marker in lowered for marker in ["we ", "this ", "the ", "in this", "although", "because"]):
            return len(line.split()) >= 8 and line.endswith((".", ":", ";"))
        return False

    def _normalize_for_model(self, text: str) -> str:
        text = normalize_pdf_ligatures(text)
        text = re.sub(r"\n(?=\d+\s+[A-Z][A-Za-z ]{2,}\n)", "\n\n", text)
        text = re.sub(r"([A-Za-z]{3,})-\s+([a-z]{2,})", r"\1\2", text)
        text = re.sub(r"([A-Za-z]{3,})-\s*\n\s*([a-z]{2,})", r"\1\2", text)
        text = " ".join(text.split())
        text = re.sub(r"\b(?:tion|sion|ment|sentation|resentation|pre)\s+(?:model|models|network|networks|training|representations)\b", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(\d+)\s+([A-Z][A-Za-z ]{2,})\s+", r"\n\1 \2\n", text)
        return text.strip()
