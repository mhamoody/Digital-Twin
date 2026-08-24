"""Small file-backed account store for the remotely hosted pilot dashboard.

This is an application login for a controlled pilot. Institutional deployments
must replace it with OIDC or an LMS LTI 1.3 launch while keeping the same
pseudonymous reviewer identity at the API boundary.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,64}$")
ALLOWED_ROLES = {"instructor", "supervisor"}
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


class AccountConfigurationError(ValueError):
    """Raised when an account file is malformed or unsafe to use."""


@dataclass(frozen=True)
class InstructorAccount:
    username: str
    display_name: str
    role: str
    reviewer_id: str
    allowed_presentations: tuple[str, ...]
    salt: bytes
    password_hash: bytes


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise AccountConfigurationError(
            "Username must be 3-64 characters using letters, numbers, dot, dash, or underscore."
        )
    return normalized


def reviewer_id_for(username: str, role: str) -> str:
    """Return an auditable pseudonym without sending the login name to the API."""

    digest = hashlib.sha256(f"dashboard:{normalize_username(username)}".encode()).hexdigest()[:24]
    return f"{role}:{digest}"


def password_record(password: str) -> dict[str, str | int]:
    if len(password) < 12:
        raise AccountConfigurationError("Password must contain at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DKLEN
    )
    return {
        "algorithm": "scrypt",
        "n": SCRYPT_N,
        "r": SCRYPT_R,
        "p": SCRYPT_P,
        "salt": base64.b64encode(salt).decode(),
        "hash": base64.b64encode(digest).decode(),
    }


def _decode_account(username: str, record: object) -> InstructorAccount:
    if not isinstance(record, dict):
        raise AccountConfigurationError(f"Account {username!r} must be an object.")
    normalized = normalize_username(username)
    role = str(record.get("role", "")).lower()
    if role not in ALLOWED_ROLES:
        raise AccountConfigurationError(f"Account {username!r} has an invalid role.")
    display_name = str(record.get("display_name", "")).strip()
    if not display_name or len(display_name) > 100:
        raise AccountConfigurationError(f"Account {username!r} needs a valid display name.")
    presentations = record.get("allowed_presentations")
    if (
        not isinstance(presentations, list)
        or not presentations
        or any(not isinstance(item, str) or not item.strip() for item in presentations)
    ):
        raise AccountConfigurationError(
            f"Account {username!r} needs at least one allowed presentation."
        )
    password = record.get("password")
    if not isinstance(password, dict) or password.get("algorithm") != "scrypt":
        raise AccountConfigurationError(f"Account {username!r} has an invalid password record.")
    if (password.get("n"), password.get("r"), password.get("p")) != (
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
    ):
        raise AccountConfigurationError(f"Account {username!r} uses unsupported scrypt settings.")
    try:
        salt = base64.b64decode(str(password["salt"]), validate=True)
        password_hash = base64.b64decode(str(password["hash"]), validate=True)
    except (KeyError, ValueError) as error:
        raise AccountConfigurationError(
            f"Account {username!r} has an invalid password encoding."
        ) from error
    if len(salt) != 16 or len(password_hash) != SCRYPT_DKLEN:
        raise AccountConfigurationError(f"Account {username!r} has an invalid password record.")
    return InstructorAccount(
        username=normalized,
        display_name=display_name,
        role=role,
        reviewer_id=reviewer_id_for(normalized, role),
        allowed_presentations=tuple(dict.fromkeys(item.strip() for item in presentations)),
        salt=salt,
        password_hash=password_hash,
    )


def load_accounts(path: str | Path) -> dict[str, InstructorAccount]:
    account_path = Path(path)
    try:
        payload = json.loads(account_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AccountConfigurationError("The instructor account file cannot be loaded.") from error
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise AccountConfigurationError("The instructor account file must use version 1.")
    raw_accounts = payload.get("accounts")
    if not isinstance(raw_accounts, dict) or not raw_accounts:
        raise AccountConfigurationError("The instructor account file contains no accounts.")
    accounts = {
        normalize_username(username): _decode_account(username, record)
        for username, record in raw_accounts.items()
    }
    if len(accounts) != len(raw_accounts):
        raise AccountConfigurationError("The instructor account file has duplicate usernames.")
    return accounts


def authenticate(
    accounts: dict[str, InstructorAccount], username: str, password: str
) -> InstructorAccount | None:
    """Authenticate without revealing whether the supplied username exists."""

    try:
        normalized = normalize_username(username)
    except AccountConfigurationError:
        normalized = "invalid-user"
    account = accounts.get(normalized)
    salt = account.salt if account else b"\0" * 16
    expected = account.password_hash if account else b"\0" * SCRYPT_DKLEN
    actual = hashlib.scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DKLEN
    )
    if account is None or not secrets.compare_digest(actual, expected):
        return None
    return account
