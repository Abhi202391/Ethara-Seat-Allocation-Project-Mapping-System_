"""Password hashing and JWT issuing/verification for the auth system.

Uses hashlib's PBKDF2 for password hashing (stdlib only, no native
dependency like bcrypt that can fail to build on some Windows setups) and
PyJWT for stateless bearer tokens.
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

SECRET_KEY = os.environ.get("JWT_SECRET", "ethara-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours
PBKDF2_ITERATIONS = 100_000


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16).hex()
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return derived.hex(), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    derived, _ = hash_password(password, salt)
    return hmac.compare_digest(derived, expected_hash)


def create_access_token(user_id: int, role: str, employee_id: Optional[int]) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "employee_id": employee_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
