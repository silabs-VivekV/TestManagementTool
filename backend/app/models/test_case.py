from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    priority: Mapped[str | None] = mapped_column(String(20), index=True)
    technology: Mapped[str | None] = mapped_column(String(100), index=True)
    release_version: Mapped[str | None] = mapped_column(String(100), index=True)
    execution_type: Mapped[str | None] = mapped_column(String(50), index=True)
    deployment_status: Mapped[str | None] = mapped_column(String(200), index=True)
    product_line: Mapped[str | None] = mapped_column(String(200), index=True)
    suite_id: Mapped[str | None] = mapped_column(String(100), index=True)
    section_id: Mapped[str | None] = mapped_column(String(150), index=True)
    sdk_type: Mapped[str | None] = mapped_column(String(200), index=True)
    product_type: Mapped[str | None] = mapped_column(String(150), index=True)
    test_case_status: Mapped[str | None] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment", back_populates="test_case", cascade="all, delete-orphan"
    )
