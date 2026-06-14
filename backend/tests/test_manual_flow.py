import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.init_db import init_db

def test_manual_complaint_flow(client: TestClient, db: Session):
    # 0. Seed test database
    init_db(db)
    
    # 1. Fetch categories
    res_cats = client.get("/api/v1/complaints/categories")
    assert res_cats.status_code == 200
    categories = res_cats.json()
    assert len(categories) > 0
    
    # Grab the first category
    cat = categories[0]
    cat_id = cat["id"]
    
    # 2. Fetch subcategories for that category
    res_subs = client.get(f"/api/v1/complaints/categories/{cat_id}/subcategories")
    assert res_subs.status_code == 200
    subcategories = res_subs.json()
    assert len(subcategories) > 0
    
    sub = subcategories[0]
    sub_id = sub["id"]
    
    # 3. Fetch questions for the subcategory
    res_qs = client.get(f"/api/v1/complaints/subcategories/{sub_id}/questions")
    assert res_qs.status_code == 200
    questions = res_qs.json()
    
    # 4. Register a user for authenticated filing
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "manualcitizen@ccrms.gov.in",
            "mobile_number": "7777777777",
            "full_name": "Manual Citizen",
            "password": "citizenpassword"
        }
    )
    
    # Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "login_identifier": "7777777777",
            "password": "citizenpassword"
        }
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Prepare dynamic answers based on subcategory questions
    answers = []
    for q in questions:
        answers.append({
            "question_id": q["id"],
            "value": "Test Answer"
        })
        
    # 5. File a manual complaint (not anonymous, authenticated)
    complaint_payload = {
        "category_id": cat_id,
        "subcategory_id": sub_id,
        "is_anonymous": False,
        "victim_name": "Manual Citizen",
        "victim_mobile": "7777777777",
        "victim_email": "manualcitizen@ccrms.gov.in",
        "victim_gender": "Male",
        "victim_address": "123 Street, City",
        "victim_state": "Delhi",
        "fraud_description": "A manual complaint text here.",
        "answers": answers,
        "suspect_details": [
            {
                "suspect_name": "John BadGuy",
                "suspect_mobile": "9876500000",
                "suspect_email": "suspect@bad.com",
                "suspect_upi": "suspect@ybl",
                "suspect_url": "http://scam-site.com",
                "suspect_social_handle": "@scammer",
                "details": "Suspicious WhatsApp message sender"
            }
        ]
    }
    
    file_res = client.post("/api/v1/complaints/file", json=complaint_payload, headers=headers)
    assert file_res.status_code == 200
    complaint = file_res.json()
    assert complaint["victim_name"] == "Manual Citizen"
    assert complaint["is_anonymous"] is False
    assert "acknowledgement_number" in complaint
    
    complaint_id = complaint["id"]
    ack_number = complaint["acknowledgement_number"]
    
    # 6. Upload evidence files
    dummy_file = io.BytesIO(b"dummy screenshot data")
    upload_res = client.post(
        f"/api/v1/complaints/{complaint_id}/evidence",
        files={"files": ("screenshot.png", dummy_file, "image/png")},
        headers=headers
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "Files uploaded successfully" in upload_data["message"]
    assert len(upload_data["evidence"]) == 1
    
    # 7. Get user complaints (dashboard list)
    user_comps_res = client.get("/api/v1/complaints/user-complaints", headers=headers)
    assert user_comps_res.status_code == 200
    user_comps = user_comps_res.json()
    assert any(c["id"] == complaint_id for c in user_comps)
    
    # 8. Track complaint
    track_res = client.get(f"/api/v1/complaints/track?query={ack_number}")
    assert track_res.status_code == 200
    tracked_comps = track_res.json()
    assert any(c["id"] == complaint_id for c in tracked_comps)
    
    # 9. Track complaint by mobile number
    track_mobile_res = client.get(f"/api/v1/complaints/track?query=7777777777")
    assert track_mobile_res.status_code == 200
    tracked_mobile_comps = track_mobile_res.json()
    assert any(c["id"] == complaint_id for c in tracked_mobile_comps)
