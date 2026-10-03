"""Opt-in same-origin pilot sessions; signing secrets never enter the browser.

Single API process only. Restarting it logs browser users out. For replicated
hosting replace the bounded in-memory store with a shared server-side store.
The existing signed Streamlit/LMS callers are deliberately unchanged.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request, Response

from digital_twin.dashboard.auth import (
    AccountConfigurationError,
    InstructorAccount,
    authenticate,
    load_accounts,
)

from .schemas import InstructorIdentity

COOKIE = "dt_browser_session"
router = APIRouter(prefix="/api/browser", tags=["browser session"])


def fingerprint(account: InstructorAccount) -> str:
    # Password/role changes revoke sessions; grants are re-read on every request.
    return hashlib.sha256(
        account.salt + account.password_hash + account.reviewer_id.encode()
    ).hexdigest()


@dataclass
class Session:
    username: str
    fingerprint: str
    csrf: str
    created: float
    touched: float


class BrowserSessions:
    idle_seconds = 1800
    lifetime_seconds = 28800
    max_sessions = 1000

    def __init__(self, origin: str, path: str, secure: bool):
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
            or origin != f"{parsed.scheme}://{parsed.netloc}"
        ):
            raise ValueError(
                "Browser origin must be an exact http(s) origin without a trailing slash."
            )
        if not secure and not (
            parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError(
                "Insecure browser cookies are allowed only on explicit loopback HTTP origins."
            )
        if secure and parsed.scheme != "https":
            raise ValueError("Secure browser sessions require an HTTPS public origin.")
        if not re.fullmatch(r"/[A-Za-z0-9_./-]*", path) or not path.endswith("/") or ".." in path:
            raise ValueError("Browser cookie path must be an absolute directory path ending in /.")
        self.origin, self.path, self.secure = origin, path, secure
        self.sessions: dict[str, Session] = {}
        self.attempts: dict[str, deque] = {}
        self.lock = threading.RLock()

    def accounts(self):
        try:
            path = os.environ["DIGITAL_TWIN_AUTH_FILE"]
            return load_accounts(path)
        except (KeyError, AccountConfigurationError) as error:
            raise HTTPException(503, "Instructor accounts are unavailable.") from error

    def check_origin(self, request: Request):
        # Never derive the trusted origin from attacker-controlled Host/forwarded headers.
        if request.headers.get("origin") != self.origin:
            raise HTTPException(403, "This browser request has an unapproved origin.")
        if request.headers.get("x-requested-with") != "CourseTwin":
            raise HTTPException(403, "The application request header is required.")

    def throttle(self, request: Request, username: str):
        now = time.monotonic()
        client = request.client.host if request.client else "unknown"
        keys = [("all", 100), ("client:" + client, 20), ("user:" + username.lower().strip(), 10)]
        with self.lock:
            self.attempts = {
                k: deque(t for t in v if t > now - 300) for k, v in self.attempts.items()
            }
            self.attempts = {k: v for k, v in self.attempts.items() if v}
            for key, limit in keys:
                if len(self.attempts.get(key, ())) >= limit:
                    raise HTTPException(
                        429,
                        "Too many sign-in attempts. Wait five minutes.",
                        headers={"Retry-After": "300"},
                    )
            for key, _ in keys:
                self.attempts.setdefault(key, deque()).append(now)

    def purge(self, now: float):
        self.sessions = {
            key: s
            for key, s in self.sessions.items()
            if now - s.created < self.lifetime_seconds and now - s.touched < self.idle_seconds
        }

    def create(self, account: InstructorAccount, old_token: str | None):
        now = time.monotonic()
        token = secrets.token_urlsafe(32)
        record = Session(
            account.username, fingerprint(account), secrets.token_urlsafe(32), now, now
        )
        with self.lock:
            self.purge(now)
            if old_token:
                self.sessions.pop(hashlib.sha256(old_token.encode()).hexdigest(), None)
            if len(self.sessions) >= self.max_sessions:
                raise HTTPException(503, "Session capacity reached. Please try again later.")
            self.sessions[hashlib.sha256(token.encode()).hexdigest()] = record
        return token, record

    def resolve(self, request: Request):
        token = request.cookies.get(COOKIE, "")
        key = hashlib.sha256(token.encode()).hexdigest()
        now = time.monotonic()
        with self.lock:
            self.purge(now)
            record = self.sessions.get(key)
            if record is None:
                raise HTTPException(401, "Your session ended. Please sign in again.")
            account = self.accounts().get(record.username)
            if account is None or not secrets.compare_digest(
                record.fingerprint, fingerprint(account)
            ):
                self.sessions.pop(key, None)
                raise HTTPException(401, "Your account changed. Please sign in again.")
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                self.check_origin(request)
                if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), record.csrf):
                    raise HTTPException(
                        403, "Your security token is invalid. Refresh and try again."
                    )
            record.touched = now
        return account, record

    def revoke(self, token: str):
        with self.lock:
            self.sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)


def configured_sessions() -> BrowserSessions | None:
    if os.environ.get("DIGITAL_TWIN_BROWSER_ENABLED") != "1":
        return None
    if not os.environ.get("DIGITAL_TWIN_AUTH_FILE"):
        raise ValueError("Browser sessions require a configured instructor account file.")
    return BrowserSessions(
        os.environ.get("DIGITAL_TWIN_BROWSER_ORIGIN", ""),
        os.environ.get("DIGITAL_TWIN_BROWSER_PATH", "/"),
        os.environ.get("DIGITAL_TWIN_BROWSER_SECURE", "1") != "0",
    )


def store(request: Request) -> BrowserSessions:
    sessions = getattr(request.app.state, "browser_sessions", None)
    if sessions is None:
        raise HTTPException(404, "Browser sessions are not enabled.")
    return sessions


def browser_identity(request: Request) -> InstructorIdentity | None:
    if (
        getattr(request.app.state, "browser_sessions", None) is None
        or COOKIE not in request.cookies
    ):
        return None
    account, _ = store(request).resolve(request)
    return InstructorIdentity(
        reviewer_id=account.reviewer_id,
        role=account.role,
        allowed_presentations=list(account.allowed_presentations),
    )


def view(account: InstructorAccount, session: Session):
    return {
        "user": {"display_name": account.display_name, "role": account.role},
        "csrf_token": session.csrf,
    }


@router.get("/session")
def session(request: Request):
    return view(*store(request).resolve(request))


@router.post("/login")
async def login(request: Request, response: Response):
    sessions = store(request)
    sessions.check_origin(request)
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(415, "Sign-in requires JSON.")
    try:
        body = await request.json()
    except ValueError as error:
        raise HTTPException(400, "Invalid sign-in request.") from error
    # Do not let validation error responses echo passwords back to the browser/logs.
    if (
        not isinstance(body, dict)
        or set(body) != {"username", "password"}
        or not isinstance(body["username"], str)
        or not isinstance(body["password"], str)
        or not 1 <= len(body["username"]) <= 64
        or not 1 <= len(body["password"]) <= 512
    ):
        raise HTTPException(400, "Invalid sign-in request.")
    sessions.throttle(request, body["username"])
    # Scrypt is CPU work: avoid blocking the async event loop.
    from starlette.concurrency import run_in_threadpool

    account = await run_in_threadpool(
        authenticate, sessions.accounts(), body["username"], body["password"]
    )
    if account is None:
        raise HTTPException(401, "Username or password is incorrect.")
    token, record = sessions.create(account, request.cookies.get(COOKIE))
    response.set_cookie(
        COOKIE,
        token,
        max_age=sessions.lifetime_seconds,
        httponly=True,
        secure=sessions.secure,
        samesite="lax",
        path=sessions.path,
    )
    return view(account, record)


@router.post("/logout")
def logout(request: Request, response: Response):
    sessions = store(request)
    sessions.resolve(request)
    sessions.revoke(request.cookies.get(COOKIE, ""))
    response.delete_cookie(
        COOKIE, path=sessions.path, secure=sessions.secure, httponly=True, samesite="lax"
    )
    return {"signed_out": True}
