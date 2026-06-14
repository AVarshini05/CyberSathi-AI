import os
import shutil
import uuid
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.crud.crud_complaint import crud_complaint
from app.models.user import User
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    ComplaintCategoryResponse,
    ComplaintSubcategoryResponse,
    ComplaintQuestionResponse,
    ComplaintStatusUpdate,
    DashboardStats,
)
from app.services.pdf_generator import generate_acknowledgement_pdf

router = APIRouter()


@router.get("/categories", response_model=List[ComplaintCategoryResponse])
def get_categories(db: Session = Depends(deps.get_db)) -> Any:
    return crud_complaint.get_categories(db)


@router.get("/categories/{category_id}/subcategories", response_model=List[ComplaintSubcategoryResponse])
def get_subcategories(category_id: int, db: Session = Depends(deps.get_db)) -> Any:
    return crud_complaint.get_subcategories_by_category(db, category_id=category_id)


@router.get("/subcategories/{subcategory_id}/questions", response_model=List[ComplaintQuestionResponse])
def get_questions(subcategory_id: int, db: Session = Depends(deps.get_db)) -> Any:
    return crud_complaint.get_questions_by_subcategory(db, subcategory_id=subcategory_id)


@router.post("/file", response_model=ComplaintResponse)
def file_complaint(
    *,
    db: Session = Depends(deps.get_db),
    complaint_in: ComplaintCreate,
    current_user: Optional[User] = Depends(deps.get_current_user),
) -> Any:
    # If anonymous is requested, ignore current_user ID for user_id link
    uid = None if complaint_in.is_anonymous else (current_user.id if current_user else None)
    
    # If not anonymous and no current_user, prompt login
    if not complaint_in.is_anonymous and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for non-anonymous complaints.",
        )
        
    complaint = crud_complaint.create_complaint(db, obj_in=complaint_in, user_id=uid)
    return complaint


@router.get("/user-complaints", response_model=List[ComplaintResponse])
def get_user_complaints(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    # Officers and admins can view all, citizens view their own
    if current_user.role in ["officer", "admin"]:
        return crud_complaint.get_all_complaints(db)
    return crud_complaint.get_complaints_by_user(db, user_id=current_user.id)


@router.get("/track", response_model=List[ComplaintResponse])
def track_complaint(
    *,
    query: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    complaints = crud_complaint.get_by_mobile_or_ack(db, search_query=query)
    if not complaints:
        raise HTTPException(
            status_code=404,
            detail="No complaints found matching the provided Acknowledgement or Mobile number."
        )
    return complaints


@router.get("/dashboard-stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user)
) -> Any:
    uid = current_user.id if (current_user and current_user.role == "citizen") else None
    return crud_complaint.get_dashboard_stats(db, user_id=uid)


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint_details(
    complaint_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    complaint = crud_complaint.get(db, id=complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Check authorization (owner or administrative/officer user)
    if current_user.role == "citizen" and complaint.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this complaint details."
        )
    return complaint


@router.post("/{complaint_id}/evidence")
def upload_evidence(
    complaint_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user)
) -> Any:
    complaint = crud_complaint.get(db, id=complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # If complaint is not anonymous, check owner
    if not complaint.is_anonymous and current_user:
        if current_user.role == "citizen" and complaint.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized upload.")

    # Create uploads directory if not exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    uploaded_records = []
    for file in files:
        # Generate unique filename to avoid collision
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Save file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(file_path)
        
        db_ev = crud_complaint.add_evidence_file(
            db,
            complaint_id=complaint_id,
            file_name=file.filename,
            file_path=file_path,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size
        )
        uploaded_records.append({
            "id": db_ev.id,
            "file_name": db_ev.file_name,
            "file_type": db_ev.file_type,
            "file_size": db_ev.file_size
        })
        
    return {"message": "Files uploaded successfully", "evidence": uploaded_records}


@router.get("/{complaint_id}/receipt")
def download_receipt(
    complaint_id: int,
    db: Session = Depends(deps.get_db)
) -> Any:
    complaint = crud_complaint.get(db, id=complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Format details for PDF generator
    complaint_data = {
        "ack_number": complaint.acknowledgement_number,
        "category": complaint.category.name,
        "subcategory": complaint.subcategory.name,
        "submission_date": complaint.submission_timestamp.strftime("%d-%b-%Y %H:%M:%S"),
        "status": complaint.current_status,
        "victim_name": complaint.victim_name,
        "victim_mobile": complaint.victim_mobile,
        "description": complaint.fraud_description
    }
    
    # Generate verification link
    verification_url = f"http://localhost/track?query={complaint.acknowledgement_number}"
    
    pdf_buffer = generate_acknowledgement_pdf(complaint_data, verification_url)
    
    filename = f"CCRMS_ACK_{complaint.acknowledgement_number}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.put("/{complaint_id}/status", response_model=ComplaintResponse)
def update_complaint_status(
    complaint_id: int,
    status_update: ComplaintStatusUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_officer_or_admin),
) -> Any:
    complaint = crud_complaint.update_complaint_status(
        db,
        complaint_id=complaint_id,
        status_update=status_update,
        officer_id=current_user.id
    )
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


from pydantic import BaseModel
import datetime
from app.models.complaint import Complaint, ComplaintAnswer, ComplaintStatus
from app.models.suspect import SuspectReport
from app.schemas.complaint import ComplaintAnswerCreate, SuspectReportCreate

class ComplaintReviewUpdate(BaseModel):
    victim_name: Optional[str] = None
    victim_mobile: Optional[str] = None
    victim_email: Optional[str] = None
    victim_address: Optional[str] = None
    victim_state: Optional[str] = None
    fraud_description: Optional[str] = None
    answers: List[ComplaintAnswerCreate] = []
    suspect_details: List[SuspectReportCreate] = []

@router.put("/{complaint_id}/review-update", response_model=ComplaintResponse)
def review_update_complaint(
    complaint_id: int,
    obj_in: ComplaintReviewUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_officer_or_admin),
) -> Any:
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Update victim fields
    if obj_in.victim_name is not None:
        complaint.victim_name = obj_in.victim_name
    if obj_in.victim_mobile is not None:
        complaint.victim_mobile = obj_in.victim_mobile
    if obj_in.victim_email is not None:
        complaint.victim_email = obj_in.victim_email
    if obj_in.victim_address is not None:
        complaint.victim_address = obj_in.victim_address
    if obj_in.victim_state is not None:
        complaint.victim_state = obj_in.victim_state
    if obj_in.fraud_description is not None:
        complaint.fraud_description = obj_in.fraud_description
        
    # Update dynamic answers
    for ans in obj_in.answers:
        db_answer = db.query(ComplaintAnswer).filter(
            ComplaintAnswer.complaint_id == complaint_id,
            ComplaintAnswer.question_id == ans.question_id
        ).first()
        if db_answer:
            db_answer.value = ans.value
        else:
            db_answer = ComplaintAnswer(
                complaint_id=complaint_id,
                question_id=ans.question_id,
                value=ans.value
            )
            db.add(db_answer)
            
    # Update suspect details
    db.query(SuspectReport).filter(SuspectReport.complaint_id == complaint_id).delete()
    for suspect in obj_in.suspect_details:
        db_suspect = SuspectReport(
            complaint_id=complaint_id,
            suspect_name=suspect.suspect_name,
            suspect_mobile=suspect.suspect_mobile,
            suspect_email=suspect.suspect_email,
            suspect_url=suspect.suspect_url,
            suspect_upi=suspect.suspect_upi,
            suspect_social_handle=suspect.suspect_social_handle,
            details=suspect.details
        )
        db.add(db_suspect)
        
    # Finalize status to Submitted
    complaint.current_status = "Submitted"
    complaint.updated_at = datetime.datetime.utcnow()
    
    # Add history entry
    db_status = ComplaintStatus(
        complaint_id=complaint_id,
        status="Submitted",
        remarks="Complaint reviewed, corrected, and officially submitted to NCRP.",
        updated_by=current_user.id
    )
    db.add(db_status)
    
    db.commit()
    db.refresh(complaint)
    return complaint

