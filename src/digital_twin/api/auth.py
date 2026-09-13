"""Explicit development-only instructor identity boundary."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import time
from pathlib import Path
from typing import Annotated

from fastapi import Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from .schemas import InstructorIdentity


def _dashboard_secret() -> bytes:
    path = os.environ.get("DIGITAL_TWIN_API_KEY_FILE", "var/auth/api.key")
    try:
        secret = Path(path).read_bytes().strip()
    except OSError as error:
        raise HTTPException(503, "Protected API signing is not configured.") from error
    if len(secret) < 32:
        raise HTTPException(503, "Protected API signing is not configured.")
    return secret


def sign_dashboard_request(
    method: str, path: str, body: bytes, reviewer_id: str, role: str
) -> dict[str, str]:
    timestamp = str(int(time.time()))
    message = "\n".join(
        (timestamp, method.upper(), path, reviewer_id, role, hashlib.sha256(body).hexdigest())
    )
    return {
        "X-Dashboard-Timestamp": timestamp,
        "X-Dashboard-Signature": hmac.new(
            _dashboard_secret(), message.encode(), hashlib.sha256
        ).hexdigest(),
    }


def authorize_course(identity: InstructorIdentity, course_id: str | None):
    if (
        identity.allowed_presentations is not None
        and course_id not in identity.allowed_presentations
    ):
        raise HTTPException(403, "This account is not authorized for the requested course.")


IDENTITY_PATTERN = re.compile(r"^(instructor|supervisor):[A-Za-z0-9._-]{1,96}$")
ALLOWED_ROLES = {"instructor", "supervisor"}
SIGNED_PLATFORM_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
SIGNED_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SIGNED_REQUEST_TOLERANCE_SECONDS = 300
INSTRUCTOR_ID_HEADER = APIKeyHeader(
    name="X-Instructor-ID", scheme_name="InstructorIdentity", auto_error=False
)
INSTRUCTOR_ROLE_HEADER = APIKeyHeader(
    name="X-Instructor-Role", scheme_name="InstructorRole", auto_error=False
)


def require_instructor(
    request: Request,
    x_instructor_id: Annotated[str | None, Security(INSTRUCTOR_ID_HEADER)] = None,
    x_instructor_role: Annotated[str | None, Security(INSTRUCTOR_ROLE_HEADER)] = None,
    x_lms_platform: Annotated[str | None, Header(alias="X-LMS-Platform")] = None,
    x_lms_context_id: Annotated[str | None, Header(alias="X-LMS-Context-ID")] = None,
    x_lms_user_id: Annotated[str | None, Header(alias="X-LMS-User-ID")] = None,
    x_lms_timestamp: Annotated[str | None, Header(alias="X-LMS-Timestamp")] = None,
    x_lms_signature: Annotated[str | None, Header(alias="X-LMS-Signature")] = None,
) -> InstructorIdentity:
    """Validate a signed LMS request or the explicit development-only headers."""

    # Hosted mode never accepts the legacy development identity headers alone.
    if os.environ.get("DIGITAL_TWIN_AUTH_FILE"):
        from digital_twin.dashboard.auth import AccountConfigurationError, load_accounts

        stamp = request.headers.get("X-Dashboard-Timestamp", "")
        signature = request.headers.get("X-Dashboard-Signature", "")
        try:
            if abs(int(time.time()) - int(stamp)) > 60:
                raise ValueError("expired")
        except ValueError as error:
            raise HTTPException(
                401, "A current signed application identity is required."
            ) from error
        path = request.url.path + ("?" + request.url.query if request.url.query else "")
        message = "\n".join(
            (
                stamp,
                request.method.upper(),
                path,
                x_instructor_id or "",
                x_instructor_role or "",
                getattr(request.state, "body_hash", hashlib.sha256(b"").hexdigest()),
            )
        )
        expected = hmac.new(_dashboard_secret(), message.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(401, "Application request signature was rejected.")
        try:
            accounts = load_accounts(os.environ["DIGITAL_TWIN_AUTH_FILE"])
        except AccountConfigurationError as error:
            raise HTTPException(503, "Account configuration is unavailable.") from error
        account = next(
            (
                a
                for a in accounts.values()
                if a.reviewer_id == x_instructor_id and a.role == x_instructor_role
            ),
            None,
        )
        if account is None:
            raise HTTPException(403, "This instructor account is no longer available.")
        return InstructorIdentity(
            reviewer_id=account.reviewer_id,
            role=account.role,
            allowed_presentations=list(account.allowed_presentations),
        )

    signed_headers = (
        x_lms_platform,
        x_lms_context_id,
        x_lms_user_id,
        x_lms_timestamp,
        x_lms_signature,
    )
    if any(value is not None for value in signed_headers):
        if not all(signed_headers) or not x_instructor_role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The signed LMS identity headers are incomplete.",
            )
        shared_secret = os.environ.get("DIGITAL_TWIN_LMS_SHARED_SECRET")
        if not shared_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Signed LMS authentication is not configured.",
            )
        role = x_instructor_role.lower()
        if role not in ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The supplied LMS role is not allowed.",
            )
        if (
            not SIGNED_PLATFORM_PATTERN.fullmatch(x_lms_platform)
            or not SIGNED_IDENTIFIER_PATTERN.fullmatch(x_lms_context_id)
            or not SIGNED_IDENTIFIER_PATTERN.fullmatch(x_lms_user_id)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The signed LMS identity contains an invalid identifier.",
            )
        try:
            timestamp = int(x_lms_timestamp)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The LMS timestamp must be an integer Unix timestamp.",
            ) from error
        if abs(int(time.time()) - timestamp) > SIGNED_REQUEST_TOLERANCE_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The signed LMS request has expired.",
            )
        message = "\n".join(
            (
                x_lms_timestamp,
                request.method.upper(),
                request.url.path,
                x_lms_platform,
                x_lms_context_id,
                x_lms_user_id,
                role,
            )
        )
        expected = hmac.new(shared_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_lms_signature.lower()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The LMS request signature is invalid.",
            )
        reviewer_digest = hashlib.sha256(f"{x_lms_platform}:{x_lms_user_id}".encode()).hexdigest()[
            :24
        ]
        return InstructorIdentity(
            reviewer_id=f"{role}:{x_lms_platform}-{reviewer_digest}", role=role
        )

    if not x_instructor_id or not x_instructor_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Instructor identity headers are required.",
        )
    role = x_instructor_role.lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The supplied role is not allowed to access instructor endpoints.",
        )
    if not IDENTITY_PATTERN.fullmatch(x_instructor_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "X-Instructor-ID must be pseudonymous and use the "
                "instructor:<id> or supervisor:<id> form."
            ),
        )
    if not x_instructor_id.startswith(f"{role}:"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor identity prefix and role header do not match.",
        )
    return InstructorIdentity(reviewer_id=x_instructor_id, role=role)
