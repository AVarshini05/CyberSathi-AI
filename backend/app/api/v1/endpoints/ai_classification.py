from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.api.deps import get_db
from app.services import classification_service

router = APIRouter()


class ClassificationRequest(BaseModel):
    description: str


class ClassificationResponse(BaseModel):
    category_id: int
    subcategory_id: int
    category_name: str
    subcategory_name: str
    detected_language: str
    translated_text: str
    confidence: int
    keywords: List[str]
    explanation: str
    ambiguous: bool


class FeedbackRequest(BaseModel):
    description: str
    suggested_category: str
    suggested_subcategory: str
    action: str  # accepted, modified, ignored


@router.post("/classify", response_model=ClassificationResponse)
async def classify_text(request: ClassificationRequest, db: Session = Depends(get_db)):
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Description text cannot be empty.")
        
    try:
        result = classification_service.classify_complaint(request.description, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification endpoint error: {str(e)}")


@router.post("/feedback")
async def log_feedback(request: FeedbackRequest):
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Description text cannot be empty.")
    if request.action not in ["accepted", "modified", "ignored"]:
        raise HTTPException(status_code=400, detail="Action must be 'accepted', 'modified', or 'ignored'.")
        
    try:
        classification_service.log_classification_feedback(
            description=request.description,
            suggested_category_name=request.suggested_category,
            suggested_subcategory_name=request.suggested_subcategory,
            action=request.action
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback endpoint error: {str(e)}")
