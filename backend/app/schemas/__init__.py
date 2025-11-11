"""Schemas module"""
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    EmailVerificationRequest,
)
from app.schemas.profile import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileResponse,
    PhotoResponse,
    InterestTagResponse,
    InterestTagCreateRequest,
    UpdateInterestsRequest,
    LocationRequest,
    GenderEnum,
    GenderPreferenceEnum,
)

__all__ = [
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserResponse",
    "EmailVerificationRequest",
    # Profile
    "ProfileCreateRequest",
    "ProfileUpdateRequest",
    "ProfileResponse",
    "PhotoResponse",
    "InterestTagResponse",
    "InterestTagCreateRequest",
    "UpdateInterestsRequest",
    "LocationRequest",
    "GenderEnum",
    "GenderPreferenceEnum",
]
