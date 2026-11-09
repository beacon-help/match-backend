from dataclasses import dataclass
from datetime import datetime, timedelta
from datetime import timezone as tz

import jwt

from match.config import get_config

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(Exception): ...


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    issued_at: datetime


def _create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    config = get_config()
    now = datetime.now(tz.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    config = get_config()
    return _create_token(user_id, ACCESS_TOKEN_TYPE, timedelta(minutes=config.ACCESS_TOKEN_TTL_MIN))


def create_refresh_token(user_id: int) -> str:
    config = get_config()
    return _create_token(user_id, REFRESH_TOKEN_TYPE, timedelta(days=config.REFRESH_TOKEN_TTL_DAYS))


def decode_token(token: str, expected_type: str) -> TokenClaims:
    config = get_config()
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise TokenError
    if payload.get("type") != expected_type:
        raise TokenError
    try:
        # Tokens minted before iat was added count as issued at the epoch.
        return TokenClaims(
            user_id=int(payload["sub"]),
            issued_at=datetime.fromtimestamp(payload.get("iat", 0), tz.utc),
        )
    except (KeyError, ValueError):
        raise TokenError
