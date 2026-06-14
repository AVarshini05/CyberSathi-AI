import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.init_db import init_db


def test_ai_classification_endpoints(client: TestClient, db: Session):
    # 0. Seed database categories/subcategories so the classifier has categories to cache
    init_db(db)

    # 1. Test feedback endpoint
    feedback_payload = {
        "description": "Someone hacked my profile",
        "suggested_category": "Other Cyber Crime",
        "suggested_subcategory": "Social Media Hacking",
        "action": "accepted"
    }
    feedback_res = client.post("/api/v1/ai/feedback", json=feedback_payload)
    assert feedback_res.status_code == 200
    assert feedback_res.json()["status"] == "success"

    # 2. Test classify endpoint (Mocking Gemini API to test pipeline)
    mock_gemini_response = {
        "detected_language": "Telugu",
        "translated_text": "My Instagram was hacked and I am being blackmailed.",
        "category_name": "Other Cyber Crime",
        "subcategory_name": "Social Media Hacking",
        "confidence": 96,
        "keywords": ["Instagram", "Hacked", "Blackmailed"],
        "explanation": "Suggesting Social Media Hacking due to unauthorized access and threats.",
        "ambiguous": False
    }

    with patch("app.services.classification_service._classify_with_gemini", return_value=mock_gemini_response):
        classify_payload = {"description": "నా ఇన్స్టాగ్రామ్ హ్యాక్ అయింది"}
        res = client.post("/api/v1/ai/classify", json=classify_payload)
        
        assert res.status_code == 200
        data = res.json()
        assert data["detected_language"] == "Telugu"
        assert data["translated_text"] == "My Instagram was hacked and I am being blackmailed."
        assert data["category_name"] == "Other Cyber Crime"
        assert data["subcategory_name"] == "Social Media Hacking"
        assert data["confidence"] == 96
        assert data["ambiguous"] is False
        assert "keywords" in data
        assert len(data["keywords"]) == 3
        # Confirm categories mapped to correct database IDs
        assert data["category_id"] > 0
        assert data["subcategory_id"] > 0

    # 3. Test fallback classifier (When Gemini returns None or fails)
    with patch("app.services.classification_service._classify_with_gemini", return_value=None):
        classify_payload = {"description": "I lost 5000 rupees in a UPI GPay transaction scam"}
        res = client.post("/api/v1/ai/classify", json=classify_payload)
        
        assert res.status_code == 200
        data = res.json()
        assert data["detected_language"] == "Local Classifier (Fallback)"
        assert data["category_name"] == "Financial Fraud"
        assert data["subcategory_name"] == "UPI Fraud"
        assert data["confidence"] == 85
        assert data["ambiguous"] is False
        assert "upi" in data["keywords"]
        assert "gpay" in data["keywords"]


def test_ai_classification_low_confidence_edge_cases(client: TestClient, db: Session):
    # Ensure database is seeded/cached
    init_db(db)

    # 1. Test empty descriptions
    # Calling service directly (should return Unknown classification)
    from app.services.classification_service import classify_complaint
    res_direct = classify_complaint("", db)
    assert res_direct["confidence"] == 0
    assert res_direct["category_id"] == 0
    assert res_direct["subcategory_id"] == 0
    assert res_direct["category_name"] == "Unknown"
    assert res_direct["subcategory_name"] == "Unknown"
    assert res_direct["ambiguous"] is True
    
    # Calling endpoint (should return 400 Bad Request)
    res_endpoint = client.post("/api/v1/ai/classify", json={"description": ""})
    assert res_endpoint.status_code == 400
    assert "cannot be empty" in res_endpoint.json()["detail"]

    # 2. Test vague descriptions (length < 10)
    classify_payload_vague = {"description": "help"}
    res_vague = client.post("/api/v1/ai/classify", json=classify_payload_vague)
    assert res_vague.status_code == 200
    data_vague = res_vague.json()
    assert data_vague["category_id"] == 0
    assert data_vague["subcategory_id"] == 0
    assert data_vague["category_name"] == "Unknown"
    assert data_vague["subcategory_name"] == "Unknown"
    assert data_vague["ambiguous"] is True
    assert "too short or vague" in data_vague["explanation"]

    # 3. Test generic internet complaints
    # Mocking Gemini to force fallback classifier
    with patch("app.services.classification_service._classify_with_gemini", return_value=None):
        classify_payload_generic = {"description": "my internet is not working since morning"}
        res_generic = client.post("/api/v1/ai/classify", json=classify_payload_generic)
        assert res_generic.status_code == 200
        data_generic = res_generic.json()
        assert data_generic["category_id"] == 0
        assert data_generic["subcategory_id"] == 0
        assert data_generic["category_name"] == "Unknown"
        assert data_generic["subcategory_name"] == "Unknown"
        assert data_generic["ambiguous"] is True
        assert "Unable to confidently determine category" in data_generic["explanation"]

    # 4. Test descriptions with no cybercrime indicators
    with patch("app.services.classification_service._classify_with_gemini", return_value=None):
        classify_payload_no_cyber = {"description": "I walked my dog in the park today"}
        res_no_cyber = client.post("/api/v1/ai/classify", json=classify_payload_no_cyber)
        assert res_no_cyber.status_code == 200
        data_no_cyber = res_no_cyber.json()
        assert data_no_cyber["category_id"] == 0
        assert data_no_cyber["subcategory_id"] == 0
        assert data_no_cyber["category_name"] == "Unknown"
        assert data_no_cyber["subcategory_name"] == "Unknown"
        assert data_no_cyber["ambiguous"] is True
        assert "Unable to confidently determine category" in data_no_cyber["explanation"]

    # 5. Test progressive re-prompt context triggering fallback rules
    with patch("app.services.classification_service._classify_with_gemini", return_value=None):
        # Scenario A: WhatsApp blackmail
        payload_whatsapp = {"description": "help [Platform: WhatsApp, Blackmail/Threats: Yes]"}
        res_wa = client.post("/api/v1/ai/classify", json=payload_whatsapp)
        assert res_wa.status_code == 200
        data_wa = res_wa.json()
        assert data_wa["ambiguous"] is False
        assert data_wa["category_name"] == "Women and Children Related Crime"
        assert data_wa["subcategory_name"] == "Blackmail / Sextortion"

        # Scenario B: UPI fraud
        payload_upi = {"description": "someone cheated me [Platform: UPI/GPay/PhonePe, Lost Money: Yes]"}
        res_upi = client.post("/api/v1/ai/classify", json=payload_upi)
        assert res_upi.status_code == 200
        data_upi = res_upi.json()
        assert data_upi["ambiguous"] is False
        assert data_upi["category_name"] == "Financial Fraud"
        assert data_upi["subcategory_name"] == "UPI Fraud"


def test_phishing_and_target_classifications(client: TestClient, db: Session):
    init_db(db)

    # 1. Verify Phishing classification using mock Gemini
    mock_phishing_res = {
        "detected_language": "English",
        "translated_text": "I received an email claiming to be from my bank. The email asked me to verify my account. After clicking the link, my login credentials were stolen.",
        "category_name": "Other Cyber Crime",
        "subcategory_name": "Phishing",
        "confidence": 95,
        "keywords": ["email", "bank", "verify account", "credentials", "stolen"],
        "explanation": "Credential theft through fraudulent email impersonation.",
        "ambiguous": False
    }

    with patch("app.services.classification_service._classify_with_gemini", return_value=mock_phishing_res):
        payload = {"description": "I received an email claiming to be from my bank. The email asked me to verify my account. After clicking the link, my login credentials were stolen."}
        res = client.post("/api/v1/ai/classify", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["category_name"] == "Other Cyber Crime"
        assert data["subcategory_name"] == "Phishing"
        assert data["confidence"] >= 90
        assert data["ambiguous"] is False
        assert "Credential theft" in data["explanation"]

    # 2. Verify Phishing classification using local fallback classifier
    with patch("app.services.classification_service._classify_with_gemini", return_value=None):
        payload_fallback = {"description": "I clicked on a phishing link sent to my email and my bank credentials were stolen."}
        res_fallback = client.post("/api/v1/ai/classify", json=payload_fallback)
        assert res_fallback.status_code == 200
        data_fb = res_fallback.json()
        assert data_fb["category_name"] == "Other Cyber Crime"
        assert data_fb["subcategory_name"] == "Phishing"
        assert data_fb["ambiguous"] is False
        assert data_fb["confidence"] >= 80

    # 3. Verify other classifications under fallback (Sextortion, Blackmail, Fake Profile, Investment Scam)
    with patch("app.services.classification_service._classify_with_gemini", return_value=None):
        # Fake Profile
        payload = {"description": "Someone created a fake profile on Facebook using my pictures."}
        res = client.post("/api/v1/ai/classify", json=payload)
        assert res.json()["subcategory_name"] == "Fake Profile / Impersonation"

        # Investment Scam
        payload = {"description": "I joined a telegram group for stock trading and lost my investment."}
        res = client.post("/api/v1/ai/classify", json=payload)
        assert res.json()["subcategory_name"] == "Investment/Trading Scam"


def test_classification_consistency(client: TestClient, db: Session):
    init_db(db)

    payload = {"description": "My Instagram account was hacked yesterday."}
    outputs = []
    
    mock_insta_res = {
        "detected_language": "English",
        "translated_text": "My Instagram account was hacked yesterday.",
        "category_name": "Other Cyber Crime",
        "subcategory_name": "Social Media Hacking",
        "confidence": 98,
        "keywords": ["Instagram", "Hacked"],
        "explanation": "Detected unauthorized account compromise.",
        "ambiguous": False
    }

    with patch("app.services.classification_service._classify_with_gemini", return_value=mock_insta_res):
        for _ in range(5):
            res = client.post("/api/v1/ai/classify", json=payload)
            assert res.status_code == 200
            data = res.json()
            outputs.append((data["category_name"], data["subcategory_name"], data["confidence"]))

    # Verify all outputs are identical
    assert len(set(outputs)) == 1



