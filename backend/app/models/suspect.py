import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class SuspectReport(Base):
    __tablename__ = "suspect_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    complaint_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=True
    )
    suspect_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    suspect_mobile: Mapped[Optional[str]] = mapped_column(
        String(20), index=True, nullable=True
    )
    suspect_email: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, nullable=True
    )
    suspect_url: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, nullable=True
    )
    suspect_upi: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )
    suspect_social_handle: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True
    )
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )

    complaint: Mapped[Optional["Complaint"]] = relationship(
        "Complaint", back_populates="suspect_reports"
    )
