from PyGithub import Github, GithubIntegration, GithubException
from core.config import settings
import asyncio
import structlog

logger = structlog.get_logger()

integration = None
if settings.GITHUB_APP_ID and settings.GITHUB_PRIVATE_KEY:
    integration = GithubIntegration(settings.GITHUB_APP_ID, settings.GITHUB_PRIVATE_KEY)

async def with_retry(fn, max_retries: int = 5, backoff: float = 2.0):
    retries = 0
    while retries < max_retries:
        try:
            return await asyncio.to_thread(fn)
        except GithubException as e:
            if e.status in (403, 429):  # rate limit or forbidden
                delay = backoff ** retries
                logger.warning(f"GitHub rate limit hit (status {e.status}), retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
                retries += 1
            else:
                raise
    raise GithubException(429, "Max retries exceeded for GitHub API")

def get_github_client(repo_full_name: str) -> Github:
    if integration:
        def fetch_installation():
            return integration.get_repo_installation(*repo_full_name.split("/"))
        installation = with_retry(fetch_installation)
        def get_token():
            return integration.get_access_token(installation.id).token
        token = with_retry(get_token)
        return Github(token)
    if settings.GITHUB_TOKEN:
        return Github(settings.GITHUB_TOKEN)
    raise ValueError("No GitHub authentication configured (APP_ID+KEY or TOKEN)")
