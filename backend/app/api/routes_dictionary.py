from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.db.session import get_db
from app.repositories.dictionary_repository import DictionaryRepository
from app.schemas.dictionary_schema import DictionaryItemCreate, DictionaryItemRead
from app.services.dictionary_service import DictionaryService

router = APIRouter(prefix="/dictionary/items", tags=["dictionary"])


@router.post("", response_model=DictionaryItemRead)
def create_dictionary_item(payload: DictionaryItemCreate, db: Session = Depends(get_db)):
    return DictionaryService(DictionaryRepository(db)).save(payload)


@router.get("", response_model=list[DictionaryItemRead])
def list_dictionary_items(db: Session = Depends(get_db)):
    return DictionaryRepository(db).list()


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dictionary_item(item_id: str, db: Session = Depends(get_db)):
    deleted = DictionaryRepository(db).delete(item_id)
    if not deleted:
        raise not_found("Dictionary item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
