"""Schemas module"""

from app.schemas.auth import (
    EmailVerificationRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.profile import (
    GenderEnum,
    GenderPreferenceEnum,
    InterestTagCreateRequest,
    InterestTagResponse,
    LocationRequest,
    PhotoResponse,
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    UpdateInterestsRequest,
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
