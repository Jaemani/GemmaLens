from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255), default="Untitled document")
    source_type: Mapped[str] = mapped_column(String(32), default="text")
    content: Mapped[str] = mapped_column(Text)
    original_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    original_mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
