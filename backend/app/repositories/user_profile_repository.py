from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.schemas.user_profile_schema import UserProfileUpdate


class UserProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self) -> UserProfile:
        profile = self.db.scalar(select(UserProfile).order_by(UserProfile.created_at.asc()))
        if profile:
            return profile
        profile = UserProfile()
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(self, payload: UserProfileUpdate) -> UserProfile:
        profile = self.get_or_create()
        for key, value in payload.model_dump(exclude_none=True).items():
            setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile
