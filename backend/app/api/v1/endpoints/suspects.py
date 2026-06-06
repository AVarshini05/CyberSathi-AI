from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.crud.crud_complaint import crud_complaint
from app.schemas.complaint import SuspectSearchResponse

router = APIRouter()


@router.get("/search", response_model=SuspectSearchResponse)
def search_suspect_repository(
    *,
    query: str = Query(..., min_length=3, description="Search by Mobile, Email, URL, UPI ID or Social handle"),
    db: Session = Depends(deps.get_db)
) -> Any:
    results = crud_complaint.search_suspect_repository(db, query_str=query)
    
    report_count = len(results)
    
    # Evaluate risk level based on report frequencies
    if report_count == 0:
        risk_level = "Safe (No Reports)"
    elif report_count == 1:
        risk_level = "Low Risk"
    elif report_count <= 3:
        risk_level = "Medium Risk"
    else:
        risk_level = "High Risk"
        
    return {
        "query": query,
        "report_count": report_count,
        "risk_level": risk_level,
        "recent_reports": results
    }
