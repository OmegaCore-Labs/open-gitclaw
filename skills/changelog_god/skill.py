import json
import litellm
from core.config import settings
from core.lancedb_client import query_memory, add_memory
from core.github_client import get_github_client
import structlog

logger = structlog.get_logger()

class ChangelogGodSkill:
    def __init__(self):
        self.metadata = SKILLS.get("changelog_god", {})

    async def process(self, payload: dict):
        try:
            repo_full = payload.get("repository", {}).get("full_name", "unknown")
            changes = payload.get("changes", "Recent commits and merged PRs")

            gh = get_github_client(repo_full)
            repo = gh.get_repo(repo_full)

            memory = await query_memory(repo_full, "Changelog generation context")
            await add_memory(repo_full, f"Changelog request for changes: {changes[:500]}")

            prompt = self.metadata.get("prompt_template", "").replace("{{repo_name}}", repo_full) \
                                                            .replace("{{changes_summary}}", changes) \
                                                            .replace("{{memory_context}}", memory)

            response = await litellm.acompletion(
                model=settings.LITELLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result_str = response.choices[0].message.content
            result = json.loads(result_str)

            # Create GitHub release if version provided
            if "version" in result:
                repo.create_git_release(
                    tag=result["version"],
                    name=f"Release {result['version']}",
                    message=result.get("release_notes", result["changelog"]),
                    draft=False,
                    prerelease=False
                )
                logger.info(f"Created GitHub release {result['version']} for {repo_full}")

            logger.info(f"Changelog generated for {repo_full}")
            return result
        except Exception as e:
            logger.error(f"Changelog generation failed: {e}")
            return {"error": str(e)}
