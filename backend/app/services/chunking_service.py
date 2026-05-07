class ChunkingService:
    def chunk(self, text: str, max_chars: int = 1200) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []
        chunks: list[str] = []
        current = ""
        for sentence in normalized.replace("? ", "?. ").replace("! ", "!. ").split(". "):
            sentence = sentence.strip()
            if not sentence:
                continue
            if not sentence.endswith("."):
                sentence += "."
            if len(current) + len(sentence) + 1 > max_chars and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            chunks.append(current.strip())
        return chunks
