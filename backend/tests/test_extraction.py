import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.init_db import init_db


def test_entity_extraction_pipeline(client: TestClient, db: Session):
    # Seed database
    init_db(db)

    # 1. Test 1: Verify extraction of Amount, UPI, and Transaction ID
    mock_gemini_res = {
        "victim_name": {"value": "Varshini", "confidence": 95, "source": "Varshini"},
        "amount_lost": {"value": "15000", "confidence": 90, "source": "₹15000"},
        "upi_id": {"value": "varshini@ybl", "confidence": 95, "source": "varshini@ybl"},
        "transaction_id": {"value": "TXN123456", "confidence": 90, "source": "TXN123456"},
        "screenshot_mentioned": True,
        "bank_receipt_mentioned": False
    }

    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value={
        "extracted_fields": {
            "victim_name": {"value": "Varshini", "source": "Varshini", "status": "valid"},
            "amount_lost": {"value": "15000", "source": "₹15000", "status": "valid"},
            "upi_id": {"value": "varshini@ybl", "source": "varshini@ybl", "status": "valid"},
            "transaction_id": {"value": "TXN123456", "source": "TXN123456", "status": "valid"}
        },
        "confidence_scores": {
            "victim_name": 95,
            "amount_lost": 90,
            "upi_id": 95,
            "transaction_id": 90
        },
        "evidence_flags": {
            "screenshot_mentioned": True,
            "bank_receipt_mentioned": False,
            "chat_screenshot_mentioned": False,
            "video_mentioned": False,
            "audio_mentioned": False
        },
        "warnings": []
    }):
        payload = {"description": "Yesterday I lost ₹15000 through a fake UPI link. My UPI ID is varshini@ybl. Transaction ID is TXN123456."}
        res = client.post("/api/v1/ai/extract", json=payload)
        assert res.status_code == 200
        data = res.json()
        
        extracted = data["extracted_fields"]
        assert extracted["amount_lost"]["value"] == "15000"
        assert extracted["upi_id"]["value"] == "varshini@ybl"
        assert extracted["transaction_id"]["value"] == "TXN123456"
        assert data["confidence_scores"]["upi_id"] == 95


def test_entity_extraction_non_financial(client: TestClient, db: Session):
    # 2. Test 2: Verify that non-financial incident does not extract false financial fields
    init_db(db)

    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value={
        "extracted_fields": {
            "victim_name": {"value": None, "source": None, "status": "valid"},
            "amount_lost": {"value": None, "source": None, "status": "valid"},
            "upi_id": {"value": None, "source": None, "status": "valid"},
            "transaction_id": {"value": None, "source": None, "status": "valid"}
        },
        "confidence_scores": {
            "victim_name": 0,
            "amount_lost": 0,
            "upi_id": 0,
            "transaction_id": 0
        },
        "evidence_flags": {
            "screenshot_mentioned": False,
            "bank_receipt_mentioned": False,
            "chat_screenshot_mentioned": False,
            "video_mentioned": False,
            "audio_mentioned": False
        },
        "warnings": []
    }):
        payload = {"description": "నా ఇన్స్టాగ్రామ్ అకౌంట్ హ్యాక్ అయింది."}
        res = client.post("/api/v1/ai/extract", json=payload)
        assert res.status_code == 200
        data = res.json()
        extracted = data["extracted_fields"]
        assert extracted["amount_lost"]["value"] is None
        assert extracted["upi_id"]["value"] is None
        assert extracted["transaction_id"]["value"] is None


def test_entity_extraction_regex_fallback(client: TestClient, db: Session):
    # 3. Test 3: Verify regex fallback extracts mobile, email, UPI, and txn IDs
    init_db(db)

    # Force Gemini to fail by returning None
    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=None):
        payload = {
            "description": "Yesterday I lost Rs 15000. My email is victim@test.com and phone is 9876543210. I sent money to suspect@okaxis. Transaction UTR is 998877665544."
        }
        res = client.post("/api/v1/ai/extract", json=payload)
        assert res.status_code == 200
        data = res.json()
        extracted = data["extracted_fields"]
        
        assert extracted["amount_lost"]["value"] == "15000"
        assert extracted["victim_email"]["value"] == "victim@test.com"
        assert extracted["victim_mobile"]["value"] == "9876543210"
        assert extracted["suspect_upi"]["value"] == "suspect@okaxis"
        assert extracted["transaction_id"]["value"] == "998877665544"


def test_entity_extraction_validation_needs_review(client: TestClient, db: Session):
    # 4. Test 4: Verify validation sets status to needs_review for invalid inputs
    init_db(db)

    mock_gemini_res = {
        "extracted_fields": {
            "victim_mobile": {"value": "12345", "source": "12345", "status": "valid"},
            "upi_id": {"value": "invalidupi", "source": "invalidupi", "status": "valid"}
        },
        "confidence_scores": {
            "victim_mobile": 95,
            "upi_id": 95
        },
        "evidence_flags": {
            "screenshot_mentioned": False,
            "bank_receipt_mentioned": False,
            "chat_screenshot_mentioned": False,
            "video_mentioned": False,
            "audio_mentioned": False
        },
        "warnings": []
    }

    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=mock_gemini_res):
        # Invalid mobile (5 digits) and invalid UPI (no @)
        payload = {
            "description": "My phone is 12345. My UPI ID is invalidupi."
        }
        res = client.post("/api/v1/ai/extract", json=payload)
        assert res.status_code == 200
        data = res.json()
        extracted = data["extracted_fields"]
        
        assert extracted["victim_mobile"]["status"] == "needs_review"
        assert extracted["upi_id"]["status"] == "needs_review"
        # Confidence score should be lowered to <= 40
        assert data["confidence_scores"]["victim_mobile"] <= 40
        assert data["confidence_scores"]["upi_id"] <= 40
        assert len(data["warnings"]) >= 2


def test_entity_extraction_context_and_platform_fallback(client: TestClient, db: Session):
    init_db(db)

    # Force Gemini to fail by returning None to test regex context-aware fallback
    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=None):
        # Test Case 1: Suspect mobile context
        payload = {
            "description": "Fraudster mobile number is 9876543210. I sent them Rs 15000 on WhatsApp."
        }
        res = client.post("/api/v1/ai/extract", json=payload)
        assert res.status_code == 200
        data = res.json()
        extracted = data["extracted_fields"]
        
        assert extracted["suspect_mobile"]["value"] == "9876543210"
        assert extracted["victim_mobile"]["value"] is None
        assert extracted["amount_lost"]["value"] == "15000"
        assert extracted["platform"]["value"] == "WhatsApp"
        
        # Test Case 2: Ambiguous mobile number should get confidence penalty
        payload_ambiguous = {
            "description": "Phone number is 9876543210."
        }
        res_amb = client.post("/api/v1/ai/extract", json=payload_ambiguous)
        assert res_amb.status_code == 200
        data_amb = res_amb.json()
        # It maps to victim_mobile but gets needs_review status and 50 confidence
        assert data_amb["extracted_fields"]["victim_mobile"]["value"] == "9876543210"
        assert data_amb["extracted_fields"]["victim_mobile"]["status"] == "needs_review"
        assert data_amb["confidence_scores"]["victim_mobile"] == 50


def test_verification_cases_with_fallback(client: TestClient, db: Session):
    init_db(db)
    
    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=None):
        # Verification Test Case 1
        payload1 = {
            "description": "My Instagram account xyz_official was hacked. The hacker is demanding ₹5000 and threatening to leak my photos."
        }
        res1 = client.post("/api/v1/ai/extract", json=payload1)
        assert res1.status_code == 200
        data1 = res1.json()
        extracted1 = data1["extracted_fields"]
        
        assert extracted1["platform"]["value"] == "Instagram"
        assert extracted1["account_id"]["value"] == "xyz_official"
        assert extracted1["amount_demanded"]["value"] == "5000"
        assert extracted1["threat_type"]["value"] == "Photo Leak"
        assert extracted1["blackmail_indicator"]["value"] is True
        assert extracted1["account_compromised"]["value"] is True

        # Verification Test Case 2
        payload2 = {
            "description": "I lost ₹15000 through a fake WhatsApp UPI payment request."
        }
        res2 = client.post("/api/v1/ai/extract", json=payload2)
        assert res2.status_code == 200
        data2 = res2.json()
        extracted2 = data2["extracted_fields"]
        
        assert extracted2["platform"]["value"] == "WhatsApp"
        assert extracted2["amount_lost"]["value"] == "15000"

        # Verification Test Case 3
        payload3 = {
            "description": "Someone created a fake Facebook profile using my name."
        }
        res3 = client.post("/api/v1/ai/extract", json=payload3)
        assert res3.status_code == 200
        data3 = res3.json()
        extracted3 = data3["extracted_fields"]
        
        assert extracted3["platform"]["value"] == "Facebook"
        assert extracted3["impersonation_indicator"]["value"] is True


def test_entity_extraction_victim_vs_suspect_separation(client: TestClient, db: Session):
    init_db(db)
    
    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=None):
        description = "My number is 9876501234 and my UPI is victim@ybl. My email is victim@test.com. My account is 12345678901. The fraudster called from 9123456780 and asked to send to suspect@okaxis and account 98765432109."
        
        res = client.post("/api/v1/ai/extract", json={"description": description})
        assert res.status_code == 200
        data = res.json()
        extracted = data["extracted_fields"]
        
        assert extracted["victim_mobile"]["value"] == "9876501234"
        assert extracted["suspect_mobile"]["value"] == "9123456780"
        assert extracted["upi_id"]["value"] == "victim@ybl"
        assert extracted["suspect_upi"]["value"] == "suspect@okaxis"
        assert extracted["victim_email"]["value"] == "victim@test.com"
        assert extracted["account_number"]["value"] == "12345678901"
        assert extracted["suspect_account_number"]["value"] == "98765432109"


def test_entity_extraction_sextortion_vs_blackmail(client: TestClient, db: Session):
    init_db(db)
    
    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=None):
        # Case 1: Simple photo leak threat -> Blackmail (no sextortion)
        payload1 = {"description": "The hacker is threatening to leak my photos on Instagram."}
        res1 = client.post("/api/v1/ai/extract", json=payload1)
        data1 = res1.json()
        assert data1["extracted_fields"]["blackmail_indicator"]["value"] is True
        assert data1["extracted_fields"]["sextortion_indicator"]["value"] is False
        assert data1["extracted_fields"]["threat_type"]["value"] == "Photo Leak"

        # Case 2: Nude/private video threat -> Sextortion
        payload2 = {"description": "He is threatening to leak my nude video if I don't pay."}
        res2 = client.post("/api/v1/ai/extract", json=payload2)
        data2 = res2.json()
        assert data2["extracted_fields"]["blackmail_indicator"]["value"] is True
        assert data2["extracted_fields"]["sextortion_indicator"]["value"] is True
        assert data2["extracted_fields"]["threat_type"]["value"] == "Sextortion"


def test_entity_extraction_false_username_rejection(client: TestClient, db: Session):
    init_db(db)
    
    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=None):
        payload = {"description": "someone created a fake profile using my name"}
        res = client.post("/api/v1/ai/extract", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["extracted_fields"]["account_id"]["value"] is None
        assert data["confidence_scores"]["account_id"] == 0


def test_entity_extraction_never_guess_values(client: TestClient, db: Session):
    init_db(db)
    
    mock_hallucinated = {
        "extracted_fields": {
            "victim_mobile": {"value": "9988776655", "source": "hallucinated", "status": "valid"},
            "account_id": {"value": "hacked_user", "source": "hacked_user", "status": "valid"}
        },
        "confidence_scores": {
            "victim_mobile": 90,
            "account_id": 90
        },
        "evidence_flags": {
            "screenshot_mentioned": False,
            "bank_receipt_mentioned": False,
            "chat_screenshot_mentioned": False,
            "video_mentioned": False,
            "audio_mentioned": False
        },
        "warnings": []
    }
    
    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=mock_hallucinated):
        payload = {"description": "Someone hacked my account. My username is hacked_user."}
        res = client.post("/api/v1/ai/extract", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["extracted_fields"]["victim_mobile"]["value"] is None
        assert data["confidence_scores"]["victim_mobile"] == 0
        assert data["extracted_fields"]["account_id"]["value"] == "hacked_user"


def test_entity_extraction_consistency(client: TestClient, db: Session):
    init_db(db)
    
    payload = {"description": "Yesterday I lost Rs 15000 through a fake UPI request on WhatsApp."}
    
    mock_gemini_res = {
        "extracted_fields": {
            "amount_lost": {"value": "15000", "source": "Rs 15000", "status": "valid"},
            "platform": {"value": "WhatsApp", "source": "WhatsApp", "status": "valid"}
        },
        "confidence_scores": {
            "amount_lost": 95,
            "platform": 95
        },
        "evidence_flags": {
            "screenshot_mentioned": False,
            "bank_receipt_mentioned": False,
            "chat_screenshot_mentioned": False,
            "video_mentioned": False,
            "audio_mentioned": False
        },
        "warnings": []
    }
    
    outputs = []
    with patch("app.services.entity_extraction_service._extract_with_gemini", return_value=mock_gemini_res):
        for _ in range(5):
            res = client.post("/api/v1/ai/extract", json=payload)
            assert res.status_code == 200
            data = res.json()
            outputs.append((
                data["extracted_fields"]["amount_lost"]["value"],
                data["extracted_fields"]["platform"]["value"],
                data["confidence_scores"]["amount_lost"]
            ))
            
    assert len(set(outputs)) == 1

