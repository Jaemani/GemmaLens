from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.user_profile_schema import UserProfileRead, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserProfileRead)
def get_profile(db: Session = Depends(get_db)):
    return UserProfileRepository(db).get_or_create()


@router.patch("", response_model=UserProfileRead)
def update_profile(payload: UserProfileUpdate, db: Session = Depends(get_db)):
    return UserProfileRepository(db).update(payload)
