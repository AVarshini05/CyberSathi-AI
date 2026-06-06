import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notification_type: Mapped[str] = mapped_column(String(20))  # sms, email, push
    recipient: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent, failed
