from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog
from core.config import settings

logger = structlog.get_logger()
security = HTTPBearer(auto_error=False)

async def rbac_check(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Placeholder for real RBAC / Vault integration.
    In production: validate JWT, check roles against Vault policies, etc.
    """
    if not credentials:
        logger.warning(f"Unauthorized access attempt to {request.url.path}")
        raise HTTPException(status_code=401, detail="Authorization required")

    token = credentials.credentials
    # TODO: real validation (Vault JWT check, role lookup)
    if token != "valid-demo-token":  # replace with real logic
        logger.warning(f"Invalid token for {request.url.path}")
        raise HTTPException(status_code=403, detail="Forbidden - invalid credentials")

    logger.debug(f"RBAC passed for {request.url.path}")
    return token

# Middleware version (apply globally if desired)
async def rbac_middleware(request: Request, call_next):
    if request.url.path.startswith(("/webhook", "/metrics")):
        # Webhooks use GitHub signature, metrics public
        return await call_next(request)
    try:
        await rbac_check(request)
    except HTTPException as e:
        return e
    response = await call_next(request)
    return response
