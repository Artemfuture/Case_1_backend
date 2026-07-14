from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _generate_uuid() -> str:
    return str(uuid4())


class CheckRecord(Base):
    __tablename__ = "checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    program: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    status_label: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    extracted: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    documents: Mapped[list["CheckDocumentRecord"]] = relationship(
        back_populates="check",
        cascade="all, delete-orphan",
        order_by="CheckDocumentRecord.version",
    )


class CheckDocumentRecord(Base):
    __tablename__ = "check_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    check_id: Mapped[str] = mapped_column(ForeignKey("checks.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    size_kb: Mapped[float] = mapped_column(Float, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    check: Mapped[CheckRecord] = relationship(back_populates="documents")
