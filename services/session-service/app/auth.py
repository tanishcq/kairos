import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Same secret as user-service, so tokens it signs can be verified here.
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be set to at least 32 characters (openssl rand -hex 32)")

JWT_ALGORITHM = "HS256"


def current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
) -> int:
    """The user id ("sub") from a valid login token issued by user-service, else 401."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        return int(payload["sub"])
    except jwt.InvalidTokenError, ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


CurrentUserId = Annotated[int, Depends(current_user_id)]
