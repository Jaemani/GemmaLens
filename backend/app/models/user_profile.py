from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    display_name: Mapped[str] = mapped_column(String(120), default="Local learner")
    target_level: Mapped[str] = mapped_column(String(32), default="C1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
