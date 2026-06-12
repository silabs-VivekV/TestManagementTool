from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ExecutionStatus


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assigned_to: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[ExecutionStatus] = mapped_column(
        String(20), default=ExecutionStatus.NOT_STARTED, index=True, nullable=False
    )
    remarks: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    evidence_link: Mapped[str | None] = mapped_column(String(1000))
    defect_info: Mapped[str | None] = mapped_column(Text)
    jira_ticket: Mapped[str | None] = mapped_column(String(100))
    eta: Mapped[date | None] = mapped_column(Date, index=True)
    execution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="assignments")
    assignee: Mapped["User"] = relationship(
        "User", foreign_keys=[assigned_to], back_populates="assignments_received"
    )
