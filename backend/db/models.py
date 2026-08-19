"""
db/models.py
────────────
SQLAlchemy ORM model for the audit_results table.

Each row represents one ``POST /api/analyze`` request — storing the uploaded
image URL (Cloudinary), the typed description, compliance results, and the
ML health grade.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class AuditResult(Base):
    """
    Persistent record of a single product label compliance analysis.

    Fields
    ------
    id                  : Auto-incrementing primary key.
    created_at          : UTC timestamp — set automatically on insert.
    description_text    : The user-typed product description (may be empty).
    image_url           : Cloudinary ``secure_url`` of the uploaded label image.
    compliance_results  : Full list of compliance check results (JSON).
    health_grade        : A–E grade from the ML service, or None if unavailable.
    health_flags        : List of flagged ingredient strings from the ML service.
    health_advice       : Qualitative advice string from the ML service.
    contradictions      : Fields where OCR and description disagreed (JSON).
    """

    __tablename__ = "audit_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    compliance_results: Mapped[list[Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="List of {field, passed, citation} dicts from the rule engine",
    )

    health_grade: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        comment="A–E grade from ML service, null if ML service was unavailable",
    )

    health_flags: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="List of flagged ingredient strings from ML service",
    )

    health_advice: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Qualitative advice from ML service",
    )

    contradictions: Mapped[list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Fields where OCR and description values disagreed",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditResult id={self.id} grade={self.health_grade!r} "
            f"created_at={self.created_at}>"
        )
