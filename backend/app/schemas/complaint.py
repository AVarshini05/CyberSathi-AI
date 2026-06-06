import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr


# Category & Subcategory Schemas
class ComplaintCategoryResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ComplaintSubcategoryResponse(BaseModel):
    id: int
    category_id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# Questions & Answers Schemas
class ComplaintQuestionResponse(BaseModel):
    id: int
    subcategory_id: int
    field_name: str
    field_label: str
    field_type: str
    is_required: bool
    field_options: Optional[str] = None

    class Config:
        from_attributes = True


class ComplaintAnswerCreate(BaseModel):
    question_id: int
    value: str


class ComplaintAnswerResponse(BaseModel):
    id: int
    question_id: int
    value: str
    field_name: Optional[str] = None
    field_label: Optional[str] = None

    class Config:
        from_attributes = True


# Suspect Schemas
class SuspectReportCreate(BaseModel):
    suspect_name: Optional[str] = None
    suspect_mobile: Optional[str] = None
    suspect_email: Optional[str] = None
    suspect_url: Optional[str] = None
    suspect_upi: Optional[str] = None
    suspect_social_handle: Optional[str] = None
    details: Optional[str] = None


class SuspectReportResponse(BaseModel):
    id: int
    complaint_id: Optional[int] = None
    suspect_name: Optional[str] = None
    suspect_mobile: Optional[str] = None
    suspect_email: Optional[str] = None
    suspect_url: Optional[str] = None
    suspect_upi: Optional[str] = None
    suspect_social_handle: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# Evidence Schemas
class EvidenceFileResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_size: int
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True


# Status History Schemas
class ComplaintStatusResponse(BaseModel):
    id: int
    status: str
    remarks: Optional[str] = None
    updated_by: Optional[int] = None
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class ComplaintStatusUpdate(BaseModel):
    status: str
    remarks: Optional[str] = None


# Complaint Creation & Response Schemas
class ComplaintCreate(BaseModel):
    category_id: int
    subcategory_id: int
    is_anonymous: bool = False
    victim_name: Optional[str] = None
    victim_mobile: Optional[str] = None
    victim_email: Optional[EmailStr] = None
    victim_gender: Optional[str] = None
    victim_address: Optional[str] = None
    victim_state: Optional[str] = None
    fraud_description: str
    answers: List[ComplaintAnswerCreate] = []
    suspect_details: List[SuspectReportCreate] = []


class ComplaintResponse(BaseModel):
    id: int
    acknowledgement_number: str
    user_id: Optional[int] = None
    category_id: int
    subcategory_id: int
    is_anonymous: bool
    victim_name: Optional[str] = None
    victim_mobile: Optional[str] = None
    victim_email: Optional[str] = None
    victim_gender: Optional[str] = None
    victim_address: Optional[str] = None
    victim_state: Optional[str] = None
    fraud_description: str
    current_status: str
    submission_timestamp: datetime.datetime
    created_at: datetime.datetime

    category: ComplaintCategoryResponse
    subcategory: ComplaintSubcategoryResponse
    answers: List[ComplaintAnswerResponse] = []
    evidence_files: List[EvidenceFileResponse] = []
    status_history: List[ComplaintStatusResponse] = []
    suspect_reports: List[SuspectReportResponse] = []

    class Config:
        from_attributes = True


class SuspectSearchResponse(BaseModel):
    query: str
    report_count: int
    risk_level: str  # Safe, Low, Medium, High
    recent_reports: List[SuspectReportResponse] = []


class DashboardStats(BaseModel):
    total_complaints: int
    open_complaints: int
    closed_complaints: int
    draft_complaints: int
