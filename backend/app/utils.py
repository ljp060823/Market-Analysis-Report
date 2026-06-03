import os
import structlog
from fastapi import Header, HTTPException
from jose import JWTError, jwt

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(20))
logger = structlog.get_logger()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    logger.warning("jwt_secret_key_not_set", message="JWT_SECRET_KEY 未设置，使用默认密钥（仅限开发环境）")
    SECRET_KEY = "dev-secret-change-me-in-production"

def verify_jwt(authorization: str | None = Header(default=None)) -> str:
    # Dev mode: allow running without auth header.
    if not authorization:
        return "local-dev-user"

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except JWTError:
        raise HTTPException(401, "Invalid token")