import asyncio
import structlog
from git import Repo, GitCommandError
from pathlib import Path
from core.repo_graph import build_graph
from core.lancedb_client import add_memory
from core.webhook_handler import get_monitored_repos, add_monitored_repo
from core.config import settings

logger = structlog.get_logger()

class RepoIndexer:
    async def index_repo(self, repo_full: str):
        safe_name = repo_full.replace("/", "_").replace("-", "_")
        local_path = Path(settings.DATA_DIR) / "repos" / safe_name

        try:
            if not local_path.exists():
                logger.info(f"Cloning new repo: {repo_full}")
                Repo.clone_from(f"https://github.com/{repo_full}.git", local_path)
            else:
                logger.debug(f"Pulling updates for {repo_full}")
                repo = Repo(local_path)
                repo.remotes.origin.pull()
        except GitCommandError as e:
            logger.error(f"Git error for {repo_full}: {e}")
            return

        await build_graph(str(local_path))
        await add_memory(repo_full, f"Repo {repo_full} indexed. Graph size: {len(function_graph)} functions.")
        logger.info(f"Successfully indexed {repo_full}")

    async def index_all_repos(self):
        repos = await get_monitored_repos()
        if not repos:
            logger.info("No monitored repos yet - waiting for first webhook")
            return
        tasks = [self.index_repo(repo) for repo in repos]
        await asyncio.gather(*tasks, return_exceptions=True)

indexer = RepoIndexer()
