from app.repositories.dictionary_repository import DictionaryRepository
from app.schemas.dictionary_schema import DictionaryItemCreate


class DictionaryService:
    def __init__(self, repository: DictionaryRepository):
        self.repository = repository

    def save(self, data: DictionaryItemCreate):
        return self.repository.create_or_increment(data)
