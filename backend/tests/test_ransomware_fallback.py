import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.init_db import init_db
from app.services.classification_service import classify_complaint
from app.services.entity_extraction_service import extract_entities


def test_ransomware_fallback_cases(client: TestClient, db: Session):
    # Ensure database is seeded/cached
    init_db(db)

    # Force Gemini to fail by returning None to test local fallback classifier and entity extraction
    with patch("app.services.classification_service._classify_with_gemini", return_value=None), \
         patch("app.services.entity_extraction_service._extract_with_gemini", return_value=None):

        # Case 1: "All files were encrypted and attackers demanded 0.5 Bitcoin."
        desc1 = "All files were encrypted and attackers demanded 0.5 Bitcoin."
        class_res1 = classify_complaint(desc1, db)
        assert class_res1["category_name"] == "Other Cyber Crime"
        assert class_res1["subcategory_name"] == "Ransomware / Malware Attack"
        assert class_res1["confidence"] >= 85
        
        extract_res1 = extract_entities(desc1)
        extracted1 = extract_res1["extracted_fields"]
        assert extracted1["amount_demanded"]["value"] == "0.5"
        assert extracted1["amount_demanded"]["amount"] == "0.5"
        assert extracted1["amount_demanded"]["currency"] == "Bitcoin"
        assert "Bitcoin" in extracted1["amount_demanded"]["source_text"]
        assert extracted1["crypto_type"]["value"] == "BTC"
        assert extracted1["crypto_type"]["status"] == "valid"

        # Case 2: "A phishing email attachment infected my laptop and all files now have .locked extension."
        desc2 = "A phishing email attachment infected my laptop and all files now have .locked extension."
        class_res2 = classify_complaint(desc2, db)
        assert class_res2["category_name"] == "Other Cyber Crime"
        assert class_res2["subcategory_name"] == "Ransomware / Malware Attack"

        # Case 3: "The attacker sent a wallet address bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4 and demanded 2 BTC."
        desc3 = "The attacker sent a wallet address bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4 and demanded 2 BTC."
        extract_res3 = extract_entities(desc3)
        extracted3 = extract_res3["extracted_fields"]
        assert extracted3["amount_demanded"]["value"] == "2"
        assert extracted3["amount_demanded"]["amount"] == "2"
        assert extracted3["amount_demanded"]["currency"] == "BTC"
        assert extracted3["crypto_wallet_address"]["value"] == "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
        assert extracted3["crypto_type"]["value"] == "BTC"

        # Case 4: "My files were encrypted and I paid ₹50,000."
        desc4 = "My files were encrypted and I paid ₹50,000."
        class_res4 = classify_complaint(desc4, db)
        assert class_res4["category_name"] == "Other Cyber Crime"
        assert class_res4["subcategory_name"] == "Ransomware / Malware Attack"
        
        extract_res4 = extract_entities(desc4)
        extracted4 = extract_res4["extracted_fields"]
        assert extracted4["amount_lost"]["value"] == "50000"
        assert extracted4["amount_lost"]["amount"] == "50000"
        assert extracted4["amount_lost"]["currency"] == "₹"

        # Case 5: Victim Name & Claimed Identity
        desc5 = "My name is Rajesh. I received a call from someone claiming to be a CBI Officer."
        extract_res5 = extract_entities(desc5)
        extracted5 = extract_res5["extracted_fields"]
        assert extracted5["victim_name"]["value"] == "Rajesh"
        assert extracted5["claimed_identity"]["value"] == "Cbi Officer"
