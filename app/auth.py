from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Any


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    """Return PBKDF2 hash in format: pbkdf2_sha256$iterations$salt$hash."""
    iterations = 210_000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    if "$" not in password_hash:
        return hmac.compare_digest(_legacy_sha256(password), password_hash)

    algorithm, iterations_str, salt, expected_hex = password_hash.split("$", 3)
    if algorithm != "pbkdf2_sha256":
        return False

    iterations = int(iterations_str)
    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return hmac.compare_digest(computed.hex(), expected_hex)


@dataclass
class AdminSession:
    token: str
    username: str
    role: str
    expires_at: datetime


class AdminSessionManager:
    def __init__(self, ttl_minutes: int = 480) -> None:
        self.ttl_minutes = ttl_minutes
        self._sessions: dict[str, AdminSession] = {}

    def create_session(self, username: str, role: str = "admin") -> AdminSession:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=self.ttl_minutes)
        session = AdminSession(token=token, username=username, role=role, expires_at=expires_at)
        self._sessions[token] = session
        return session

    def get_session(self, token: str) -> AdminSession | None:
        session = self._sessions.get(token)
        if not session:
            return None
        if session.expires_at < datetime.utcnow():
            self._sessions.pop(token, None)
            return None
        return session


def extract_bearer_token(headers: Any) -> str | None:
    authorization = headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token or None


def get_authorized_admin(
    headers: Any,
    admin_api_key: str,
    session_manager: AdminSessionManager | None = None,
) -> dict[str, str] | None:
    provided_key = headers.get("X-Admin-Key")
    if provided_key and provided_key == admin_api_key:
        return {"username": "api_key_admin", "role": "admin", "authType": "api_key"}

    if session_manager:
        token = extract_bearer_token(headers)
        if token:
            session = session_manager.get_session(token)
            if session:
                return {"username": session.username, "role": session.role, "authType": "bearer"}

    return None


def is_admin_authorized(headers: Any, admin_api_key: str, session_manager: AdminSessionManager | None = None) -> bool:
    return get_authorized_admin(headers, admin_api_key, session_manager) is not None
