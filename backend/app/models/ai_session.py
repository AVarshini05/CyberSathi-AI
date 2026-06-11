import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base


class AISession(Base):
    __tablename__ = "ai_sessions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # UUID session ID
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    state: Mapped[str] = mapped_column(String(50), default="GREETING")  # conversation state
    detected_category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("complaint_categories.id", ondelete="SET NULL"), nullable=True)
    detected_subcategory_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("complaint_subcategories.id", ondelete="SET NULL"), nullable=True)
    collected_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)  # all extracted form data
    conversation_history: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)  # list of {role, message, timestamp}
    language: Mapped[str] = mapped_column(String(20), default="en-IN")  # detected/selected language
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
