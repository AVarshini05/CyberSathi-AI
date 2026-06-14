from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.api import deps
from app.crud.crud_user import crud_user
from app.schemas.user import UserCreate, UserResponse, UserLogin, OTPRequest, OTPVerify
from app.schemas.token import Token
from app.models.notification import Notification

router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
) -> Any:
    # Check if mobile exists
    user_mob = crud_user.get_by_mobile(db, mobile_number=user_in.mobile_number)
    if user_mob:
        raise HTTPException(
            status_code=400,
            detail="A user with this mobile number already exists in the system.",
        )
    # Check if email exists
    if user_in.email:
        user_email = crud_user.get_by_email(db, email=user_in.email)
        if user_email:
            raise HTTPException(
                status_code=400,
                detail="A user with this email address already exists in the system.",
            )
    user = crud_user.create(db, obj_in=user_in)
    return user


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    # OAuth2 standard Form uses username, which we map to login_identifier
    user = crud_user.authenticate(
        db, login_identifier=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email/mobile number or password",
        )
    elif not crud_user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email/mobile number or password",
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/login", response_model=Token)
def login(
    *,
    db: Session = Depends(deps.get_db),
    login_in: UserLogin,
) -> Any:
    user = crud_user.authenticate(
        db, login_identifier=login_in.login_identifier, password=login_in.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email/mobile number or password",
        )
    elif not crud_user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email/mobile number or password",
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/otp/request")
def request_otp(
    *,
    db: Session = Depends(deps.get_db),
    otp_req: OTPRequest,
) -> Any:
    # Simulates sending an OTP to the citizen
    user = crud_user.get_by_mobile(db, mobile_number=otp_req.mobile_number)
    
    # Send simulation
    otp_code = "123456"  # Simulated static OTP for dev purposes
    msg = f"CyberSathi-AI: Your login verification code is {otp_code}. Valid for 5 minutes."
    
    db_notif = Notification(
        user_id=user.id if user else None,
        notification_type="sms",
        recipient=otp_req.mobile_number,
        message=msg,
        status="sent"
    )
    db.add(db_notif)
    db.commit()

    return {
        "message": f"OTP successfully sent via SMS to {otp_req.mobile_number}",
        "otp_code_dev_only": otp_code  # Exposing to client for simulator convenience
    }


@router.post("/otp/verify", response_model=Token)
def verify_otp(
    *,
    db: Session = Depends(deps.get_db),
    otp_verify: OTPVerify,
) -> Any:
    # Simulates verifying an OTP and logging in
    if otp_verify.otp != "123456":
        raise HTTPException(status_code=400, detail="Invalid OTP code entered.")
        
    user = crud_user.get_by_mobile(db, mobile_number=otp_verify.mobile_number)
    if not user:
        # Auto-register user or return not found?
        # Standard NCRP allows quick registration, but let's assume they must register first.
        raise HTTPException(
            status_code=404,
            detail="Mobile number not registered. Please register first.",
        )
        
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/test-token", response_model=UserResponse)
def test_token(current_user: Any = Depends(deps.get_current_user)) -> Any:
    return current_user
