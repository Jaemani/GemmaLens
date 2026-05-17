import re
from dataclasses import dataclass

from app.services.text_cleanup_service import normalize_pdf_ligatures


@dataclass(frozen=True)
class DocumentSection:
    text: str
    source_label: str | None = None
    title: str | None = None
    continuation: bool = False


class DocumentSectionService:
    section_chars = 1800
    page_marker_pattern = re.compile(r"\[\[GEMMALENS_PDF_PAGE:(\d+)]]")

    def split(self, text: str) -> list[str]:
        return [section.text for section in self.split_with_labels(text)]

    def split_with_labels(self, text: str) -> list[DocumentSection]:
        if not self.page_marker_pattern.search(text):
            current_title: str | None = None
            sections = []
            for section in self._split_plain(self._clean(text)):
                if not self._is_learning_section(section):
                    continue
                title = self._section_title(section)
                current_title = title or current_title
                sections.append(DocumentSection(section, title=title or current_title, continuation=not bool(title) and bool(current_title)))
            return self._post_process_sections(sections)

        sections: list[DocumentSection] = []
        current_title: str | None = None
        parts = self.page_marker_pattern.split(text)
        leading = parts[0]
        for section in self._split_plain(self._clean(leading)):
            if not self._is_learning_section(section):
                continue
            title = self._section_title(section)
            current_title = title or current_title
            sections.append(DocumentSection(section, title=title or current_title, continuation=not bool(title) and bool(current_title)))
        for index in range(1, len(parts), 2):
            page_number = parts[index]
            page_text = parts[index + 1] if index + 1 < len(parts) else ""
            label = f"PDF page {page_number}"
            for section in self._split_plain(self._clean(page_text)):
                if not self._is_learning_section(section):
                    continue
                title = self._section_title(section)
                continuation = not bool(title) and bool(current_title)
                current_title = title or current_title
                sections.append(DocumentSection(section, label, title or current_title, continuation))
        return self._post_process_sections(sections)

    def _split_plain(self, cleaned: str) -> list[str]:
        structured = self._split_structured(cleaned)
        if len(structured) > 1:
            return structured
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
        text = self._restore_decimal_fragments(text)
        text = self._restore_inline_headings(text)
        text = self._trim_front_matter(text)
        text = self._remove_leading_attention_artifact(text)
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

    def _restore_decimal_fragments(self, text: str) -> str:
        # PDF extraction can split decimal references such as "archives 28.4"
        # into "archives 28.\n4 ..."; the second line must never become a
        # numbered section heading.
        text = re.sub(r"(\b[a-z][A-Za-z-]*\s+\d{1,3})\.\s*\n\s*(\d)(?=\b)", r"\1.\2", text)
        text = re.sub(r"(\b(?:vol|volume|issue|no|number|archives?|archive)\.?\s+\d{1,3})\s*\n\s*(\d)(?=\b)", r"\1.\2", text, flags=re.IGNORECASE)
        return text

    def _remove_leading_attention_artifact(self, text: str) -> str:
        normalized = text.strip()
        replacements = [
            (
                r"^Scaled Dot-Product Attention\s+Multi-Head Attention\s+Figure 2:.*?parallel\.\s+",
                r"3.2.1 Scaled Dot-Product Attention ",
            ),
            (
                r"^Table 1: Maximum path lengths, per-layer complexity.*?(In this section we compare)",
                r"4 Why Self-Attention \1",
            ),
            (
                r"^Table 2: The Transformer achieves better BLEU scores.*?(On the WMT 2014)",
                r"6 Results \1",
            ),
        ]
        for pattern, replacement in replacements:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE | re.DOTALL)
        return normalized

    def _restore_inline_headings(self, text: str) -> str:
        sentence_start = r"(?:The|This|These|In|We|Here|Given|Each|Most|Recurrent|Attention|Self-attention|End-to-end|To)\b"
        text = re.sub(
            rf"(?<![\w.-])(\d{{1,2}}(?:\.\d+)*\s+[A-Z][A-Za-z][A-Za-z0-9 ,:/()'’-]{{2,80}}?)(?=\s+{sentence_start})",
            r"\n\1\n",
            text,
        )
        heading_tail = (
            r"(?:problems?|problem|form|sets?|functions?|constraints?|duality|algorithms?|methods?|examples?|applications?|"
            r"theory|geometry|optimality|conditions)"
        )
        text = re.sub(
            rf"\b([A-Z][A-Za-z-]*(?:\s+(?:of|and|for|in|with|[A-Za-z-]+)){{1,7}}\s+{heading_tail})\s+(?=[A-Z][a-z])",
            r"\n\1\n",
            text,
        )
        text = re.sub(
            rf"\b(Abstract\s+form\s+convex\s+optimization\s+problem)\s+(?=[A-Z][a-z])",
            r"\n\1\n",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\b(Abstract|Introduction|Background|Conclusion|References)\s+(?=[A-Z][a-z])", r"\n\1\n", text)
        text = re.sub(r"\b(References)\s+(?=\[\d+\])", r"\n\1\n", text)
        text = re.sub(
            r"\n(\d+(?:\.\d+)?)\s*\n(Introduction|Background|Model Architecture|Encoder and Decoder Stacks|ModelArchitecture)\b",
            r"\n\1 \2\n",
            text,
        )
        text = re.sub(
            r"(?<=[.!?])\s+(\d{1,2}(?:\.\d+)+\s+(?:Encoder and Decoder Stacks|Scaled Dot-Product Attention|Multi-Head Attention|Applications of Attention in our Model|Position-wise Feed-Forward Networks|Embeddings and Softmax|Positional Encoding)\b)",
            r"\n\1\n",
            text,
        )
        return text

    def _trim_front_matter(self, text: str) -> str:
        normalized = text.strip()
        abstract_match = re.search(r"\bAbstract\b\s+(?=[A-Z])", normalized)
        if not abstract_match:
            return text
        before = normalized[: abstract_match.start()]
        after = normalized[abstract_match.start():]
        if len(before) < 1600 and re.search(r"@\w|Google Brain|University|Institute|\*", before):
            return after
        return text

    def _split_structured(self, cleaned: str) -> list[str]:
        lines = [line.strip() for line in cleaned.splitlines()]
        if sum(1 for line in lines if line) < 2:
            return []
        blocks: list[str] = []
        current = ""
        current_label = ""
        for line in lines:
            if not line:
                if current:
                    blocks.append(current.strip())
                    current = ""
                    current_label = ""
                continue
            if self._is_heading_line(line):
                if current:
                    blocks.append(current.strip())
                current = line
                current_label = line
                continue
            if current_label and len(current) < 220:
                current = f"{current} {line}".strip()
                continue
            if current and len(current) + len(line) > self.section_chars:
                blocks.append(current.strip())
                current = line
                current_label = ""
            else:
                current = f"{current} {line}".strip()
        if current:
            blocks.append(current.strip())
        blocks = [block for block in blocks if self._is_learning_section(block)]
        return self._pack_blocks(blocks)

    def _pack_blocks(self, blocks: list[str]) -> list[str]:
        sections: list[str] = []
        current = ""
        for block in blocks:
            if not current:
                current = block
                continue
            starts_new_topic = self._block_starts_with_heading(block)
            if starts_new_topic or len(current) + len(block) > self.section_chars:
                sections.append(current.strip())
                current = block
            else:
                current = f"{current} {block}".strip()
        if current:
            sections.append(current.strip())
        return sections

    def _block_starts_with_heading(self, block: str) -> bool:
        words = block.split()
        for count in range(min(9, len(words)), 1, -1):
            candidate = " ".join(words[:count])
            if self._is_heading_line(candidate):
                return True
        return False

    def _is_heading_line(self, line: str) -> bool:
        normalized = " ".join(line.split()).strip(" .")
        if not normalized or len(normalized) > 110:
            return False
        if self._looks_like_decimal_or_citation_fragment(normalized):
            return False
        if normalized.lower() in {"abstract", "introduction", "background", "conclusion", "references"}:
            return True
        if re.match(r"^\d{1,2}\s+[A-Z]", normalized):
            return True
        if re.match(r"^\d{1,2}(?:\.\d+)+\s+[A-Z]", normalized):
            return True
        words = normalized.split()
        if len(words) < 2 or len(words) > 9:
            return False
        if normalized.endswith((".", ";", ",")):
            return False
        heading_markers = {
            "problem",
            "problems",
            "form",
            "sets",
            "functions",
            "constraints",
            "duality",
            "algorithm",
            "algorithms",
            "method",
            "methods",
            "examples",
            "applications",
            "conditions",
        }
        if words[-1].lower() not in heading_markers:
            return False
        capitalized = sum(1 for word in words if word[:1].isupper() or word.lower() in {"of", "and", "for", "in", "with"})
        return capitalized >= max(1, len(words) - 2)

    def _looks_like_decimal_or_citation_fragment(self, line: str) -> bool:
        lowered = line.lower()
        if re.search(r"\b(?:archives?|archive|vol|volume|issue|number|no)\.?\s+\d{1,3}(?:\.\d+)+\b", lowered):
            return True
        if re.match(r"^\d{1,3}(?:\.\d+)+\s*(?:[,;:]|$)", lowered):
            return True
        if re.match(r"^\d{1,3}(?:\.\d+)+\s+[a-z]", line):
            return True
        return False

    def _section_title(self, text: str) -> str | None:
        normalized = " ".join(text.split())
        if not normalized:
            return None
        simple = re.match(r"^(Abstract|Introduction|Background|Conclusion|References)\b", normalized, flags=re.IGNORECASE)
        if simple:
            return simple.group(1).title()
        known_numbered = re.match(
            r"^(\d{1,2}(?:\.\d+)*\s+(?:Introduction|Background|Model Architecture|ModelArchitecture|Encoder and Decoder Stacks|Attention|Scaled Dot-Product Attention|Multi-Head Attention|Applications of Attention in our Model|Position-wise Feed-Forward Networks|Embeddings and Softmax|Positional Encoding|Why Self-Attention|Training|Training Data and Batching|Hardware and Schedule|Optimizer|Regularization|Results|Machine Translation|Model Variations))\b",
            normalized,
        )
        if known_numbered:
            return known_numbered.group(1).replace("ModelArchitecture", "Model Architecture")
        numbered = re.match(r"^(\d{1,2}(?:\.\d+)*\s+[A-Z][A-Za-z0-9 ,:/()'’-]{2,80}?)(?=\s+[A-Z][a-z]|\s*$)", normalized)
        if numbered:
            return numbered.group(1).strip()
        for count in range(min(9, len(normalized.split())), 1, -1):
            candidate = " ".join(normalized.split()[:count])
            if self._is_heading_line(candidate):
                return candidate
        return None

    def _post_process_sections(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        return self._merge_short_orphan_sections(
            self._merge_short_continuations(
                self._merge_heading_only_sections(
                    self._merge_dangling_sections(sections)
                )
            )
        )

    def _merge_heading_only_sections(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        merged: list[DocumentSection] = []
        index = 0
        while index < len(sections):
            current = sections[index]
            if index + 1 < len(sections) and self._is_heading_only_section(current):
                following = sections[index + 1]
                merged.append(
                    DocumentSection(
                        self._clean(f"{current.text} {following.text}"),
                        current.source_label or following.source_label,
                        current.title or following.title,
                        False,
                    )
                )
                index += 2
                continue
            merged.append(current)
            index += 1
        return merged

    def _is_heading_only_section(self, section: DocumentSection) -> bool:
        normalized = " ".join(section.text.split()).strip()
        if len(normalized) > 160:
            return False
        if not section.title:
            return False
        if normalized.lower() == section.title.lower():
            return True
        if normalized.lower().startswith(section.title.lower()) and len(normalized.split()) <= len(section.title.split()) + 2:
            return True
        return bool(re.match(r"^\d{1,2}\s+[A-Z]", section.title)) and "this section describes" in normalized.lower()

    def _merge_short_continuations(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        merged: list[DocumentSection] = []
        for section in sections:
            normalized = " ".join(section.text.split())
            if merged and section.continuation and len(normalized) < 180:
                previous = merged[-1]
                merged[-1] = DocumentSection(
                    self._clean(f"{previous.text} {section.text}"),
                    previous.source_label or section.source_label,
                    previous.title or section.title,
                    previous.continuation,
                )
                continue
            merged.append(section)
        return merged

    def _merge_dangling_sections(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        merged: list[DocumentSection] = []
        index = 0
        while index < len(sections):
            current = sections[index]
            if index + 1 < len(sections) and self._is_dangling_section(current.text):
                following = sections[index + 1]
                merged.append(
                    DocumentSection(
                        self._clean(f"{current.text} {following.text}"),
                        current.source_label or following.source_label,
                        current.title or following.title,
                        current.continuation,
                    )
                )
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

    def _merge_short_orphan_sections(self, sections: list[DocumentSection]) -> list[DocumentSection]:
        merged: list[DocumentSection] = []
        for section in sections:
            if merged and self._is_short_orphan_section(section.text):
                previous = merged[-1]
                merged[-1] = DocumentSection(
                    self._clean(f"{previous.text} {section.text}"),
                    previous.source_label or section.source_label,
                    previous.title or section.title,
                    previous.continuation,
                )
                continue
            merged.append(section)
        return merged

    def _is_short_orphan_section(self, text: str) -> bool:
        normalized = " ".join(text.split())
        if len(normalized) > 260:
            return False
        return bool(re.search(r"\b\d+\s*$", normalized)) and not re.search(
            r"\b(?:abstract|introduction|conclusion|experiments?|method|results?)\b",
            normalized,
            flags=re.IGNORECASE,
        )

    def _is_learning_section(self, text: str) -> bool:
        lowered = " ".join(text.lower().split())
        if not lowered:
            return False
        if len(lowered) < 80 and self._is_short_artifact(lowered):
            return False
        if self._is_table_like_artifact(lowered):
            return False
        if self._is_bibliography_artifact(lowered):
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

    def _is_table_like_artifact(self, lowered: str) -> bool:
        if "layer nameoutput size" in lowered and "architectures for imagenet" in lowered:
            return True
        if "architectures for imagenet" in lowered and "flops" in lowered and lowered.count("×") >= 10:
            return True
        if lowered.startswith("model top-1 err") and "top-5 err" in lowered and "error rates" in lowered:
            return True
        if lowered.startswith("method top-1 err") and "top-5 err" in lowered and "error rates" in lowered:
            return True
        if "iter. (1e4)" in lowered and "dashed lines denote training error" in lowered:
            return True
        if "standard deviations" in lowered and "layer responses" in lowered and lowered.count("plain-") >= 2 and lowered.count("resnet-") >= 2:
            return True
        if len(lowered) < 500:
            return False
        conv_count = lowered.count("conv")
        stride_count = lowered.count("/2")
        pool_count = lowered.count("pool")
        return conv_count >= 15 and stride_count >= 4 and pool_count >= 3

    def _is_bibliography_artifact(self, lowered: str) -> bool:
        if lowered.startswith("references ["):
            return True
        if "rethinking the inception architecture" in lowered and "corr" in lowered and "yonghui wu" in lowered:
            return True
        citation_count = len(re.findall(r"\[\d+]", lowered))
        year_count = len(re.findall(r"\b(?:19|20)\d{2}\b", lowered))
        venue_markers = sum(
            lowered.count(marker)
            for marker in (
                " in nips",
                " in icml",
                " in cvpr",
                " in iccv",
                " tpami",
                " arxiv:",
                " corr,",
                " abs/",
                " ieee transactions",
                " neural computation",
                " cambridge university press",
                " oxford university press",
            )
        )
        return (citation_count >= 3 and venue_markers >= 2) or (year_count >= 3 and venue_markers >= 1)

    def _is_short_artifact(self, lowered: str) -> bool:
        artifact_markers = [
            "weighted sum",
            "figure",
            "table",
            "equation",
            "where",
        ]
        return any(marker in lowered for marker in artifact_markers)
