import hmac
import hashlib
import httpx
import asyncio
import json
import redis.asyncio as aioredis
import aiosqlite
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
import structlog
from core.config import settings
from core.planner import planner
from core.github_client import get_github_client

logger = structlog.get_logger()
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

ALLOWED_IPS = set()
IDEMPOTENCY_DB = Path(settings.DATA_DIR) / "idempotency.db"
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
STREAM_NAME = "opengitclaw_events"
DLQ_NAME = "opengitclaw_dlq"

async def init_idempotency_db():
    async with aiosqlite.connect(IDEMPOTENCY_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                delivery_id TEXT PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monitored_repos (
                repo_full TEXT PRIMARY KEY
            )
        """)
        await db.commit()
    logger.info("Idempotency & repo DB initialized")

async def is_duplicate(delivery_id: str) -> bool:
    async with aiosqlite.connect(IDEMPOTENCY_DB) as db:
        cursor = await db.execute("SELECT 1 FROM events WHERE delivery_id = ?", (delivery_id,))
        return bool(await cursor.fetchone())

async def record_event(delivery_id: str):
    async with aiosqlite.connect(IDEMPOTENCY_DB) as db:
        await db.execute("INSERT OR IGNORE INTO events (delivery_id) VALUES (?)", (delivery_id,))
        await db.commit()

async def add_monitored_repo(repo_full: str):
    async with aiosqlite.connect(IDEMPOTENCY_DB) as db:
        await db.execute("INSERT OR IGNORE INTO monitored_repos (repo_full) VALUES (?)", (repo_full,))
        await db.commit()

async def get_monitored_repos() -> list[str]:
    async with aiosqlite.connect(IDEMPOTENCY_DB) as db:
        cursor = await db.execute("SELECT repo_full FROM monitored_repos")
        rows = await cursor.fetchall()
    return [row[0] for row in rows]

async def refresh_github_ips():
    global ALLOWED_IPS
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("https://api.github.com/meta")
            data = resp.json()
            ALLOWED_IPS = set(data.get("hooks", []))
            logger.info(f"GitHub webhook IPs refreshed: {len(ALLOWED_IPS)} IPs")
        except Exception as e:
            logger.error(f"Failed to refresh GitHub IPs: {e}")

@router.middleware("http")
async def ip_and_rate_limit(request: Request, call_next):
    if request.url.path.startswith("/webhook"):
        if request.client.host not in ALLOWED_IPS and ALLOWED_IPS:
            logger.warning(f"Blocked request from unauthorized IP: {request.client.host}")
            raise HTTPException(403, "IP not in GitHub allowlist")
        # Rate limit: 30/min per IP
        response = await limiter.limit("30/minute")(call_next)(request)
    else:
        response = await call_next(request)
    return response

async def verify_signature(body: bytes, signature: str):
    if not signature or not settings.WEBHOOK_SECRET:
        raise HTTPException(403, "Signature missing or secret not set")
    expected = "sha256=" + hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(403, "Invalid webhook signature")

@router.post("/")
async def github_webhook(request: Request):
    signature = request.headers.get("X-Hub-Signature-256")
    body = await request.body()
    await verify_signature(body, signature)

    payload = await request.json()
    event = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")

    if await is_duplicate(delivery_id):
        logger.info(f"Duplicate delivery ignored: {delivery_id}")
        return {"status": "duplicate"}

    await record_event(delivery_id)

    # Auto-add repo to monitored list
    repo_full = payload.get("repository", {}).get("full_name")
    if repo_full:
        await add_monitored_repo(repo_full)

    # Get diff early for PR events
    pr_diff = ""
    if event == "pull_request":
        repo_full = payload["repository"]["full_name"]
        pr_num = payload["pull_request"]["number"]
        gh = get_github_client(repo_full)
        repo = gh.get_repo(repo_full)
        pr = repo.get_pull(pr_num)
        pr_diff = httpx.get(pr.diff_url).text

    # Publish to Redis stream
    await redis_client.xadd(
        STREAM_NAME,
        {
            "payload": json.dumps(payload),
            "event": event or "unknown",
            "pr_diff": pr_diff
        }
    )

    return {"status": "accepted"}
