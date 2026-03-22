from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.auth_service import auth_service
from app.schemas.auth import (
    EmailSignupRequest, EmailLoginRequest, OTPVerifyRequest, 
    ResendOTPRequest, PasswordResetRequestSchema, 
    PasswordResetConfirmSchema, AuthResponse, UserPublic,
    SignupResponse
)
from app.models.user import User

router = APIRouter()

@router.post("/signup", response_model=SignupResponse)
async def signup(
    request: EmailSignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with email and password. 
    Sends a 6-digit OTP to the email.
    """
    try:
        user = await auth_service.register_email_user(
            db=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            country=request.country
        )
        return {"message": "OTP sent to your email", "email": user.email}
    except HTTPException as e:
        raise e
    except Exception as e:
        import logging
        logging.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )

@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify the 6-digit OTP sent to the email.
    Returns access token on success.
    """
    token, user = await auth_service.verify_otp(
        db=db,
        email=request.email,
        otp_code=request.otp_code
    )
    return {"access_token": token, "user": user}

@router.post("/resend-otp")
async def resend_otp(
    request: ResendOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend a new 6-digit OTP if the previous one expired.
    """
    await auth_service.resend_otp(db=db, email=request.email)
    return {"message": "Verification code resent"}

@router.post("/login", response_model=AuthResponse)
async def login(
    request: EmailLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    """
    token, user = await auth_service.login_email(
        db=db,
        email=request.email,
        password=request.password
    )
    return {"access_token": token, "user": user}

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequestSchema,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a password reset link.
    """
    await auth_service.request_password_reset(db=db, email=request.email)
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirmSchema,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm password reset using the token from email.
    """
    await auth_service.confirm_password_reset(
        db=db,
        token=request.token,
        new_password=request.new_password
    )
    return {"message": "Password updated successfully"}

@router.get("/me", response_model=UserPublic)
async def get_me(user: User = Depends(auth_service.get_current_user)):
    """
    Get current logged in user profile.
    """
    return user
