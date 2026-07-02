from datetime import datetime, timedelta
from datetime import timezone as tz

import jwt
from pwdlib import PasswordHash

from match.config import get_config

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

_password_hash = PasswordHash.recommended()


class TokenError(Exception): ...


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


def _create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    config = get_config()
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "exp": datetime.now(tz.utc) + expires_delta,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    config = get_config()
    return _create_token(user_id, ACCESS_TOKEN_TYPE, timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN))


def create_refresh_token(user_id: int) -> str:
    config = get_config()
    return _create_token(user_id, REFRESH_TOKEN_TYPE, timedelta(days=config.REFRESH_TOKEN_TTL_DAYS))


def decode_token(token: str, expected_type: str) -> int:
    config = get_config()
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise TokenError
    if payload.get("type") != expected_type:
        raise TokenError
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise TokenError
