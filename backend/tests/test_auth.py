def test_register_citizen(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@ccrms.gov.in",
            "mobile_number": "9876543210",
            "full_name": "Test Citizen",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@ccrms.gov.in"
    assert data["mobile_number"] == "9876543210"
    assert data["full_name"] == "Test Citizen"
    assert "id" in data


def test_login_citizen(client):
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginuser@cybersathi.gov.in",
            "mobile_number": "9876543211",
            "full_name": "Login Citizen",
            "password": "loginpassword"
        }
    )
    
    # Login by mobile number
    response = client.post(
        "/api/v1/auth/login",
        json={
            "login_identifier": "9876543211",
            "password": "loginpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_citizen_by_email(client):
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "emailuser@cybersathi.gov.in",
            "mobile_number": "9876543288",
            "full_name": "Email Login Citizen",
            "password": "loginpassword"
        }
    )
    
    # Login by email (lowercase)
    response = client.post(
        "/api/v1/auth/login",
        json={
            "login_identifier": "emailuser@cybersathi.gov.in",
            "password": "loginpassword"
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

    # Login by email (case-insensitive check)
    response_case = client.post(
        "/api/v1/auth/login",
        json={
            "login_identifier": "EMAILUSER@CYBERSATHI.GOV.IN",
            "password": "loginpassword"
        }
    )
    assert response_case.status_code == 200
    assert "access_token" in response_case.json()


def test_login_failure(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "login_identifier": "nonexistent@cybersathi.gov.in",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email/mobile number or password"


def test_otp_simulation(client):
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "otpuser@cybersathi.gov.in",
            "mobile_number": "9876543212",
            "full_name": "OTP Citizen",
            "password": "otppassword"
        }
    )
    
    # Request OTP
    response = client.post(
        "/api/v1/auth/otp/request",
        json={"mobile_number": "9876543212"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "successfully sent" in data["message"]
    
    # Verify OTP and login
    verify_response = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "mobile_number": "9876543212",
            "otp": "123456"
        }
    )
    assert verify_response.status_code == 200
    verify_data = verify_response.json()
    assert "access_token" in verify_data
