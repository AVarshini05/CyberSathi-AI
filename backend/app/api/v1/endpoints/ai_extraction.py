from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from app.services import entity_extraction_service

router = APIRouter()


class ExtractionRequest(BaseModel):
    description: str


class ExtractionResponse(BaseModel):
    extracted_fields: Dict[str, Any]
    confidence_scores: Dict[str, int]
    evidence_flags: Dict[str, bool]
    warnings: List[str]


@router.post("/extract", response_model=ExtractionResponse)
async def extract_incident_entities(request: ExtractionRequest):
    if not request.description.strip():
        raise HTTPException(status_code=400, detail="Description text cannot be empty.")
        
    try:
        result = entity_extraction_service.extract_entities(request.description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction endpoint error: {str(e)}")
