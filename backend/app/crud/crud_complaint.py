import datetime
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func
from app.models.complaint import (
    Complaint,
    ComplaintCategory,
    ComplaintSubcategory,
    ComplaintQuestion,
    ComplaintAnswer,
    EvidenceFile,
    ComplaintStatus,
)
from app.models.suspect import SuspectReport
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.schemas.complaint import ComplaintCreate, ComplaintStatusUpdate, SuspectReportCreate


class CRUDComplaint:
    def get_category_by_id(self, db: Session, category_id: int) -> Optional[ComplaintCategory]:
        return db.query(ComplaintCategory).filter(ComplaintCategory.id == category_id).first()

    def get_subcategory_by_id(self, db: Session, subcategory_id: int) -> Optional[ComplaintSubcategory]:
        return db.query(ComplaintSubcategory).filter(ComplaintSubcategory.id == subcategory_id).first()

    def get_categories(self, db: Session) -> List[ComplaintCategory]:
        return db.query(ComplaintCategory).all()

    def get_subcategories_by_category(self, db: Session, category_id: int) -> List[ComplaintSubcategory]:
        return db.query(ComplaintSubcategory).filter(ComplaintSubcategory.category_id == category_id).all()

    def get_questions_by_subcategory(self, db: Session, subcategory_id: int) -> List[ComplaintQuestion]:
        return db.query(ComplaintQuestion).filter(ComplaintQuestion.subcategory_id == subcategory_id).all()

    def get(self, db: Session, id: Any) -> Optional[Complaint]:
        return db.query(Complaint).filter(Complaint.id == id).first()

    def get_by_ack(self, db: Session, ack_number: str) -> Optional[Complaint]:
        return db.query(Complaint).filter(Complaint.acknowledgement_number == ack_number).first()

    def get_by_mobile_or_ack(self, db: Session, search_query: str) -> List[Complaint]:
        # Search by ACK number or victim mobile number
        return db.query(Complaint).filter(
            or_(
                Complaint.acknowledgement_number == search_query,
                Complaint.victim_mobile == search_query
            )
        ).all()

    def create_complaint(
        self, db: Session, *, obj_in: ComplaintCreate, user_id: Optional[int] = None, status: str = "Submitted"
    ) -> Complaint:
        # 1. Fetch category code
        category = db.query(ComplaintCategory).filter(ComplaintCategory.id == obj_in.category_id).first()
        cat_code = category.code if category else "GEN"

        # 2. Sequential ACK Number Auto-Increment logic (Safe transaction)
        current_year = datetime.datetime.now().year
        # Count complaints in this category and year
        prefix = f"CYBERSATHI-{cat_code}-{current_year}-"
        count = db.query(Complaint).filter(
            Complaint.acknowledgement_number.like(f"{prefix}%")
        ).count() + 1
        ack_number = f"{prefix}{count:06d}"

        # 3. Create main Complaint
        db_complaint = Complaint(
            acknowledgement_number=ack_number,
            user_id=user_id,
            category_id=obj_in.category_id,
            subcategory_id=obj_in.subcategory_id,
            is_anonymous=obj_in.is_anonymous,
            victim_name=obj_in.victim_name,
            victim_mobile=obj_in.victim_mobile,
            victim_email=obj_in.victim_email,
            victim_gender=obj_in.victim_gender,
            victim_address=obj_in.victim_address,
            victim_state=obj_in.victim_state,
            fraud_description=obj_in.fraud_description,
            current_status=status,
        )
        db.add(db_complaint)
        db.flush()  # Gets the database-assigned complaint ID

        # 4. Insert Answers for Dynamic Questions
        for ans in obj_in.answers:
            db_answer = ComplaintAnswer(
                complaint_id=db_complaint.id,
                question_id=ans.question_id,
                value=ans.value
            )
            db.add(db_answer)

        # 5. Insert Suspect Details
        for suspect in obj_in.suspect_details:
            db_suspect = SuspectReport(
                complaint_id=db_complaint.id,
                suspect_name=suspect.suspect_name,
                suspect_mobile=suspect.suspect_mobile,
                suspect_email=suspect.suspect_email,
                suspect_url=suspect.suspect_url,
                suspect_upi=suspect.suspect_upi,
                suspect_social_handle=suspect.suspect_social_handle,
                details=suspect.details
            )
            db.add(db_suspect)

        # 6. Add initial status history
        db_status = ComplaintStatus(
            complaint_id=db_complaint.id,
            status=status,
            remarks="Complaint registered successfully through Voice Agent." if status == "Pending Employee Review" else "Complaint registered successfully.",
            updated_by=user_id
        )
        db.add(db_status)

        # 7. Simulate Notification (SMS & Email)
        notification_message = (
            f"Your cybercrime complaint has been registered successfully. "
            f"Acknowledgement Number: {ack_number}. "
            f"Please use this number for future tracking."
        )
        
        # SMS Notification Log
        if obj_in.victim_mobile:
            sms_notif = Notification(
                user_id=user_id,
                notification_type="sms",
                recipient=obj_in.victim_mobile,
                message=notification_message,
                status="sent"
            )
            db.add(sms_notif)

        # Email Notification Log
        if obj_in.victim_email:
            email_notif = Notification(
                user_id=user_id,
                notification_type="email",
                recipient=obj_in.victim_email,
                message=notification_message,
                status="sent"
            )
            db.add(email_notif)

        # 8. Log Audit Activity
        audit_log = AuditLog(
            user_id=user_id,
            action="COMPLAINT_FILED",
            details=f"Complaint filed successfully with ACK: {ack_number}"
        )
        db.add(audit_log)

        db.commit()
        db.refresh(db_complaint)
        return db_complaint

    def get_complaints_by_user(self, db: Session, user_id: int) -> List[Complaint]:
        return db.query(Complaint).filter(Complaint.user_id == user_id).order_by(Complaint.created_at.desc()).all()

    def get_all_complaints(
        self,
        db: Session,
        *,
        ack_number: Optional[str] = None,
        mobile_number: Optional[str] = None,
        citizen_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Complaint]:
        query = db.query(Complaint)
        if ack_number:
            query = query.filter(Complaint.acknowledgement_number == ack_number)
        if mobile_number:
            query = query.filter(Complaint.victim_mobile == mobile_number)
        if citizen_name:
            query = query.filter(Complaint.victim_name.ilike(f"%{citizen_name}%"))
        if status:
            query = query.filter(Complaint.current_status == status)
        return query.order_by(Complaint.created_at.desc()).all()

    def update_complaint_status(
        self, db: Session, *, complaint_id: int, status_update: ComplaintStatusUpdate, officer_id: int
    ) -> Optional[Complaint]:
        db_complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not db_complaint:
            return None

        # Update main complaint status
        db_complaint.current_status = status_update.status
        db_complaint.updated_at = datetime.datetime.utcnow()

        # Add history entry
        db_status = ComplaintStatus(
            complaint_id=complaint_id,
            status=status_update.status,
            remarks=status_update.remarks,
            updated_by=officer_id
        )
        db.add(db_status)

        # Log audit activity
        audit_log = AuditLog(
            user_id=officer_id,
            action="COMPLAINT_STATUS_UPDATED",
            details=f"Complaint status of ID {complaint_id} updated to {status_update.status}"
        )
        db.add(audit_log)

        db.commit()
        db.refresh(db_complaint)
        return db_complaint

    def add_evidence_file(
        self, db: Session, *, complaint_id: int, file_name: str, file_path: str, file_type: str, file_size: int
    ) -> EvidenceFile:
        db_evidence = EvidenceFile(
            complaint_id=complaint_id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size
        )
        db.add(db_evidence)
        db.commit()
        db.refresh(db_evidence)
        return db_evidence

    def search_suspect_repository(self, db: Session, query_str: str) -> List[SuspectReport]:
        # Search across multiple suspect parameters
        return db.query(SuspectReport).filter(
            or_(
                SuspectReport.suspect_mobile == query_str,
                SuspectReport.suspect_email == query_str,
                SuspectReport.suspect_url.ilike(f"%{query_str}%"),
                SuspectReport.suspect_upi == query_str,
                SuspectReport.suspect_social_handle.ilike(f"%{query_str}%")
            )
        ).all()

    def get_dashboard_stats(self, db: Session, user_id: Optional[int] = None) -> dict:
        query = db.query(Complaint)
        if user_id is not None:
            query = query.filter(Complaint.user_id == user_id)
            
        total = query.count()
        open_count = query.filter(Complaint.current_status.in_(["Submitted", "Under Review", "Assigned", "Investigation In Progress", "Additional Information Required"])).count()
        closed_count = query.filter(Complaint.current_status == "Closed").count()
        draft_count = query.filter(Complaint.current_status == "Pending Employee Review").count()

        return {
            "total_complaints": total,
            "open_complaints": open_count,
            "closed_complaints": closed_count,
            "draft_complaints": draft_count
        }


crud_complaint = CRUDComplaint()
