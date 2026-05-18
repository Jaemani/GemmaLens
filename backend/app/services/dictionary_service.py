from app.repositories.dictionary_repository import DictionaryRepository
from app.schemas.dictionary_schema import DictionaryItemCreate


class DictionaryService:
    def __init__(self, repository: DictionaryRepository):
        self.repository = repository

    def save(self, data: DictionaryItemCreate):
        return self.repository.create_or_increment(self._with_fallback_meaning(data))

    def _with_fallback_meaning(self, data: DictionaryItemCreate) -> DictionaryItemCreate:
        if data.meaning and data.meaning.strip():
            return data
        source = (data.source_sentence or "").strip()
        text = data.text.strip()
        if data.item_type == "concept":
            meaning = f"{text} is a concept saved from the source material."
        elif data.item_type == "phrase":
            meaning = "Spoken or academic expression saved from the source material."
        elif data.item_type == "sentence":
            meaning = "Sentence pattern saved from the source material."
        else:
            meaning = "Term saved from the source material."
        if source:
            meaning = f"{meaning} Source: {source}"
        return data.model_copy(update={"meaning": meaning})
