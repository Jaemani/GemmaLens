from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TargetLevel = Literal["B1", "B2", "C1", "C2", "domain-heavy", "unknown"]


class UserProfileRead(BaseModel):
    id: str
    display_name: str
    target_level: str
    support_language: str
    learning_language: str
    onboarding_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    target_level: TargetLevel | None = None
    support_language: str | None = None
    learning_language: str | None = None
    onboarding_completed: bool | None = None
