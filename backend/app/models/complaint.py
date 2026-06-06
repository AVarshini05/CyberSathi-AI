import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class ComplaintCategory(Base):
    __tablename__ = "complaint_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # FF, OC, WC
    description: Mapped[str] = mapped_column(Text, nullable=True)

    subcategories: Mapped[List["ComplaintSubcategory"]] = relationship(
        "ComplaintSubcategory", back_populates="category", cascade="all, delete-orphan"
    )
    complaints: Mapped[List["Complaint"]] = relationship(
        "Complaint", back_populates="category"
    )


class ComplaintSubcategory(Base):
    __tablename__ = "complaint_subcategories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaint_categories.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    category: Mapped["ComplaintCategory"] = relationship(
        "ComplaintCategory", back_populates="subcategories"
    )
    questions: Mapped[List["ComplaintQuestion"]] = relationship(
        "ComplaintQuestion", back_populates="subcategory", cascade="all, delete-orphan"
    )
    complaints: Mapped[List["Complaint"]] = relationship(
        "Complaint", back_populates="subcategory"
    )


class ComplaintQuestion(Base):
    __tablename__ = "complaint_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subcategory_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaint_subcategories.id", ondelete="CASCADE")
    )
    field_name: Mapped[str] = mapped_column(String(100))  # e.g., transaction_amount
    field_label: Mapped[str] = mapped_column(String(200))  # e.g., Transaction Amount
    field_type: Mapped[str] = mapped_column(String(50))  # text, number, date, select, textarea
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    field_options: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Comma separated or JSON list

    subcategory: Mapped["ComplaintSubcategory"] = relationship(
        "ComplaintSubcategory", back_populates="questions"
    )
    answers: Mapped[List["ComplaintAnswer"]] = relationship(
        "ComplaintAnswer", back_populates="question", cascade="all, delete-orphan"
    )


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    acknowledgement_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaint_categories.id")
    )
    subcategory_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaint_subcategories.id")
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)

    # Victim details (if applicable or requested)
    victim_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    victim_mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    victim_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    victim_gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    victim_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    victim_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    fraud_description: Mapped[str] = mapped_column(Text)
    current_status: Mapped[str] = mapped_column(String(50), default="Submitted")
    submission_timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    category: Mapped["ComplaintCategory"] = relationship(
        "ComplaintCategory", back_populates="complaints"
    )
    subcategory: Mapped["ComplaintSubcategory"] = relationship(
        "ComplaintSubcategory", back_populates="complaints"
    )
    answers: Mapped[List["ComplaintAnswer"]] = relationship(
        "ComplaintAnswer", back_populates="complaint", cascade="all, delete-orphan"
    )
    evidence_files: Mapped[List["EvidenceFile"]] = relationship(
        "EvidenceFile", back_populates="complaint", cascade="all, delete-orphan"
    )
    status_history: Mapped[List["ComplaintStatus"]] = relationship(
        "ComplaintStatus", back_populates="complaint", cascade="all, delete-orphan"
    )
    suspect_reports: Mapped[List["SuspectReport"]] = relationship(
        "SuspectReport", back_populates="complaint", cascade="all, delete-orphan"
    )


class ComplaintAnswer(Base):
    __tablename__ = "complaint_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaints.id", ondelete="CASCADE")
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaint_questions.id", ondelete="CASCADE")
    )
    value: Mapped[str] = mapped_column(Text)

    complaint: Mapped["Complaint"] = relationship(
        "Complaint", back_populates="answers"
    )
    question: Mapped["ComplaintQuestion"] = relationship(
        "ComplaintQuestion", back_populates="answers"
    )


class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaints.id", ondelete="CASCADE")
    )
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )

    complaint: Mapped["Complaint"] = relationship(
        "Complaint", back_populates="evidence_files"
    )


class ComplaintStatus(Base):
    __tablename__ = "complaint_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaints.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(50))  # Submitted, Under Review, Assigned, etc.
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow
    )

    complaint: Mapped["Complaint"] = relationship(
        "Complaint", back_populates="status_history"
    )
