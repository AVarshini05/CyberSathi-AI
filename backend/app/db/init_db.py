import json
from sqlalchemy.orm import Session
from app.models.complaint import ComplaintCategory, ComplaintSubcategory, ComplaintQuestion
from app.models.user import User
from app.core.security import get_password_hash


def init_db(db: Session) -> None:
    # 1. Create Default Admin/Officer if not exist (checking by mobile number to avoid duplicates)
    admin_user = db.query(User).filter(User.mobile_number == "9999999999").first()
    if not admin_user:
        admin_user = User(
            email="admin@cybersathi.gov.in",
            mobile_number="9999999999",
            full_name="System Administrator",
            hashed_password=get_password_hash("adminpassword"),
            role="admin",
            is_active=True,
            is_superuser=True
        )
        db.add(admin_user)
    else:
        # Migrate email domain from ccrms.gov.in to cybersathi.gov.in if needed
        if admin_user.email and admin_user.email.endswith("ccrms.gov.in"):
            admin_user.email = admin_user.email.replace("ccrms.gov.in", "cybersathi.gov.in")
            db.add(admin_user)

    officer_user = db.query(User).filter(User.mobile_number == "8888888888").first()
    if not officer_user:
        officer_user = User(
            email="officer@cybersathi.gov.in",
            mobile_number="8888888888",
            full_name="Investigation Officer Ramesh",
            hashed_password=get_password_hash("officerpassword"),
            role="officer",
            is_active=True,
            is_superuser=False
        )
        db.add(officer_user)
    else:
        # Migrate email domain from ccrms.gov.in to cybersathi.gov.in if needed
        if officer_user.email and officer_user.email.endswith("ccrms.gov.in"):
            officer_user.email = officer_user.email.replace("ccrms.gov.in", "cybersathi.gov.in")
            db.add(officer_user)

    # 2. Seed Categories
    categories_data = [
        {
            "name": "Financial Fraud",
            "code": "FF",
            "description": "UPI frauds, net banking, debit/credit cards, loan apps, crypto, trading scams and other transaction frauds.",
            "subcategories": [
                {
                    "name": "UPI Fraud",
                    "description": "Fraudulent transfers using UPI PIN, QR Codes, or phishing links.",
                    "questions": [
                        {"field_name": "upi_id", "field_label": "Your UPI ID", "field_type": "text", "is_required": True},
                        {"field_name": "beneficiary_upi_id", "field_label": "Fraudulent/Beneficiary UPI ID", "field_type": "text", "is_required": True},
                        {"field_name": "transaction_id", "field_label": "Transaction ID / UTR Number", "field_type": "text", "is_required": True},
                        {"field_name": "bank_name", "field_label": "Your Bank Name", "field_type": "text", "is_required": True},
                        {"field_name": "amount", "field_label": "Transaction Amount (INR)", "field_type": "number", "is_required": True},
                        {"field_name": "transaction_date", "field_label": "Transaction Date & Time", "field_type": "datetime-local", "is_required": True}
                    ]
                },
                {
                    "name": "Internet Banking Fraud",
                    "description": "Unauthorized transfer of funds from savings/current account via net banking portal.",
                    "questions": [
                        {"field_name": "account_number", "field_label": "Your Account Number", "field_type": "text", "is_required": True},
                        {"field_name": "bank_name", "field_label": "Bank Name", "field_type": "text", "is_required": True},
                        {"field_name": "utr_number", "field_label": "UTR Number / Reference Number", "field_type": "text", "is_required": True},
                        {"field_name": "beneficiary_acc", "field_label": "Beneficiary Account Number (if known)", "field_type": "text", "is_required": False},
                        {"field_name": "amount", "field_label": "Transaction Amount (INR)", "field_type": "number", "is_required": True},
                        {"field_name": "transaction_date", "field_label": "Transaction Date & Time", "field_type": "datetime-local", "is_required": True}
                    ]
                },
                {
                    "name": "Debit/Credit Card Fraud",
                    "description": "ATM card cloning, details leakage, online unauthorized shopping, OTP fraud.",
                    "questions": [
                        {"field_name": "card_digits", "field_label": "Card Last 4 Digits", "field_type": "text", "is_required": True},
                        {"field_name": "card_type", "field_label": "Card Type", "field_type": "select", "field_options": "Debit,Credit", "is_required": True},
                        {"field_name": "bank_name", "field_label": "Card Issuing Bank", "field_type": "text", "is_required": True},
                        {"field_name": "amount", "field_label": "Transaction Amount (INR)", "field_type": "number", "is_required": True},
                        {"field_name": "transaction_date", "field_label": "Transaction Date", "field_type": "date", "is_required": True}
                    ]
                },
                {
                    "name": "Investment/Trading Scam",
                    "description": "Fake stock trading advice, fake investment apps, telegram channels promising high returns.",
                    "questions": [
                        {"field_name": "platform_name", "field_label": "Scam Platform / App Name", "field_type": "text", "is_required": True},
                        {"field_name": "social_channel", "field_label": "Telegram/WhatsApp Group link or details", "field_type": "text", "is_required": False},
                        {"field_name": "total_lost", "field_label": "Total Amount Invested (INR)", "field_type": "number", "is_required": True},
                        {"field_name": "payment_modes", "field_label": "Payment Mode used", "field_type": "select", "field_options": "UPI,Net Banking,Card,Crypto", "is_required": True}
                    ]
                },
                {
                    "name": "Loan App Fraud",
                    "description": "Instant loan apps charging high interest, blackmailing using edited contacts/photos.",
                    "questions": [
                        {"field_name": "app_name", "field_label": "Loan App Name", "field_type": "text", "is_required": True},
                        {"field_name": "download_link", "field_label": "App Download Link / Source URL", "field_type": "text", "is_required": False},
                        {"field_name": "amount_disbursed", "field_label": "Amount Received (INR)", "field_type": "number", "is_required": True},
                        {"field_name": "amount_demanded", "field_label": "Amount Demanded/Paid (INR)", "field_type": "number", "is_required": True}
                    ]
                },
                {
                    "name": "Cryptocurrency Fraud",
                    "description": "Crypto wallet hacking, fake coin sales, crypto investment sites.",
                    "questions": [
                        {"field_name": "wallet_address", "field_label": "Your Wallet Address", "field_type": "text", "is_required": True},
                        {"field_name": "crypto_type", "field_label": "Crypto Coin Type", "field_type": "select", "field_options": "BTC,ETH,USDT,BNB,Other", "is_required": True},
                        {"field_name": "fraud_wallet", "field_label": "Fraudulent/Receiver Wallet Address", "field_type": "text", "is_required": True},
                        {"field_name": "tx_hash", "field_label": "Transaction Hash (TxID)", "field_type": "text", "is_required": True},
                        {"field_name": "amount", "field_label": "Crypto Value / Lost Amount", "field_type": "number", "is_required": True}
                    ]
                }
            ]
        },
        {
            "name": "Other Cyber Crime",
            "code": "OC",
            "description": "Social media hacking, identity theft, cyberstalking, online harassment, defacement, ransomware, etc.",
            "subcategories": [
                {
                    "name": "Phishing",
                    "description": "Credential theft or sensitive information theft through fraudulent emails, links, or replica websites.",
                    "questions": [
                        {"field_name": "phishing_url", "field_label": "Phishing Link / Website", "field_type": "text", "is_required": True},
                        {"field_name": "spoofed_brand", "field_label": "Brand/Organization Impersonated", "field_type": "text", "is_required": False},
                        {"field_name": "medium", "field_label": "Medium used (Email/SMS/WhatsApp)", "field_type": "select", "field_options": "Email,SMS,WhatsApp,Other", "is_required": True},
                        {"field_name": "stolen_info", "field_label": "Information Stolen", "field_type": "select", "field_options": "Credentials,Financial Info,Personal Details,Other", "is_required": True}
                    ]
                },
                {
                    "name": "Social Media Hacking",
                    "description": "Unauthorized access to profile and locking out user.",
                    "questions": [
                        {"field_name": "platform", "field_label": "Platform Name", "field_type": "select", "field_options": "Instagram,Facebook,Twitter/X,LinkedIn,Snapchat,Other", "is_required": True},
                        {"field_name": "profile_url", "field_label": "Profile URL / Link", "field_type": "text", "is_required": True},
                        {"field_name": "username", "field_label": "Username / Handle", "field_type": "text", "is_required": True},
                        {"field_name": "last_access", "field_label": "Last Successful Access Date", "field_type": "date", "is_required": True}
                    ]
                },
                {
                    "name": "Fake Profile / Impersonation",
                    "description": "Creation of fake accounts using photos/details of another citizen to defame or harass.",
                    "questions": [
                        {"field_name": "platform", "field_label": "Platform Name", "field_type": "select", "field_options": "Instagram,Facebook,Twitter/X,LinkedIn,WhatsApp,Other", "is_required": True},
                        {"field_name": "fake_profile_url", "field_label": "Fake Profile URL / Link", "field_type": "text", "is_required": True},
                        {"field_name": "impersonator_handle", "field_label": "Fake Profile Username/Handle", "field_type": "text", "is_required": True},
                        {"field_name": "target_profile_url", "field_label": "Your Original Profile URL (Victim)", "field_type": "text", "is_required": True}
                    ]
                },
                {
                    "name": "Email Hacking",
                    "description": "Unauthorized login to email and changing recovery options.",
                    "questions": [
                        {"field_name": "email_address", "field_label": "Hacked Email Address", "field_type": "text", "is_required": True},
                        {"field_name": "recovery_email", "field_label": "Last Known Recovery Email", "field_type": "text", "is_required": False},
                        {"field_name": "last_access", "field_label": "Last Successful Access Date", "field_type": "date", "is_required": True}
                    ]
                },
                {
                    "name": "Ransomware / Malware Attack",
                    "description": "Files encrypted on computer, requesting Bitcoin payments to unlock.",
                    "questions": [
                        {"field_name": "ransomware_name", "field_label": "Ransomware Name (e.g. .lock, .wannacry)", "field_type": "text", "is_required": False},
                        {"field_name": "amount_demanded", "field_label": "Ransom Amount Demanded", "field_type": "number", "is_required": False},
                        {"field_name": "crypto_type", "field_label": "Crypto Coin Type", "field_type": "select", "field_options": "BTC,ETH,USDT,BNB,Other", "is_required": False},
                        {"field_name": "fraud_wallet", "field_label": "Fraudulent/Receiver Wallet Address", "field_type": "text", "is_required": False},
                        {"field_name": "os_affected", "field_label": "Operating System Affected", "field_type": "select", "field_options": "Windows,macOS,Linux,Android,iOS,Other", "is_required": True}
                    ]
                }
            ]
        },
        {
            "name": "Women and Children Related Crime",
            "code": "WC",
            "description": "Cyberstalking, online harassment, blackmail, sextortion, child exploitation, and obscene content.",
            "subcategories": [
                {
                    "name": "Cyber Stalking / Online Harassment",
                    "description": "Constantly monitoring or messaging a woman/child online, causing distress or safety concerns.",
                    "questions": [
                        {"field_name": "platform", "field_label": "Platform where harassment occurred", "field_type": "select", "field_options": "Instagram,Facebook,WhatsApp,Snapchat,Email,Other", "is_required": True},
                        {"field_name": "stalker_handle", "field_label": "Suspect Username/Handle/Phone", "field_type": "text", "is_required": True},
                        {"field_name": "stalker_url", "field_label": "Suspect Profile Link (if any)", "field_type": "text", "is_required": False},
                        {"field_name": "start_date", "field_label": "Incident Start Date", "field_type": "date", "is_required": True},
                        {"field_name": "is_known", "field_label": "Is Suspect Known to Victim?", "field_type": "select", "field_options": "No,Yes,Unsure", "is_required": True}
                    ]
                },
                {
                    "name": "Blackmail / Sextortion",
                    "description": "Coercing money or sexual favors by threatening to release private photos, videos, or chats.",
                    "questions": [
                        {"field_name": "platform", "field_label": "Communication Channel", "field_type": "select", "field_options": "WhatsApp,Instagram,Facebook,Video Call,Other", "is_required": True},
                        {"field_name": "demands", "field_label": "What are the suspect's demands?", "field_type": "select", "field_options": "Money,Additional Content,Other", "is_required": True},
                        {"field_name": "suspect_contact", "field_label": "Suspect Contact Info (Phone/Handle)", "field_type": "text", "is_required": True}
                    ]
                },
                {
                    "name": "Child Exploitation / Obscene Content",
                    "description": "Sharing or uploading child abuse material (CSAM) or explicit content involving minors.",
                    "questions": [
                        {"field_name": "content_url", "field_label": "Website / Platform URL where hosted", "field_type": "text", "is_required": True},
                        {"field_name": "uploaded_date", "field_label": "Date Content Noticed", "field_type": "date", "is_required": True}
                    ]
                }
            ]
        }
    ]

    for cat_data in categories_data:
        db_cat = db.query(ComplaintCategory).filter(ComplaintCategory.name == cat_data["name"]).first()
        if not db_cat:
            db_cat = ComplaintCategory(
                name=cat_data["name"],
                code=cat_data["code"],
                description=cat_data["description"]
            )
            db.add(db_cat)
            db.flush()

        for sub_data in cat_data["subcategories"]:
            db_sub = db.query(ComplaintSubcategory).filter(
                ComplaintSubcategory.category_id == db_cat.id,
                ComplaintSubcategory.name == sub_data["name"]
            ).first()
            if not db_sub:
                db_sub = ComplaintSubcategory(
                    category_id=db_cat.id,
                    name=sub_data["name"],
                    description=sub_data["description"]
                )
                db.add(db_sub)
                db.flush()

            for quest_data in sub_data["questions"]:
                db_quest = db.query(ComplaintQuestion).filter(
                    ComplaintQuestion.subcategory_id == db_sub.id,
                    ComplaintQuestion.field_name == quest_data["field_name"]
                ).first()
                if not db_quest:
                    db_quest = ComplaintQuestion(
                        subcategory_id=db_sub.id,
                        field_name=quest_data["field_name"],
                        field_label=quest_data["field_label"],
                        field_type=quest_data["field_type"],
                        field_options=quest_data.get("field_options"),
                        is_required=quest_data["is_required"]
                    )
                    db.add(db_quest)

    db.commit()
    print("Database initial categories, subcategories, questions and default admin/officer seeded successfully.")
