import json
import litellm
from core.config import settings
from core.lancedb_client import query_memory, add_memory
from core.github_client import get_github_client
import structlog

logger = structlog.get_logger()

class DocsUpdaterSkill:
    def __init__(self):
        self.metadata = SKILLS.get("docs_updater", {})

    async def process(self, payload: dict):
        try:
            repo_full = payload.get("repository", {}).get("full_name", "unknown")
            change_summary = payload.get("change_summary", "Recent code changes")

            gh = get_github_client(repo_full)
            repo = gh.get_repo(repo_full)

            memory = await query_memory(repo_full, "Documentation update context")
            await add_memory(repo_full, f"Docs update for: {change_summary[:500]}")

            prompt = self.metadata.get("prompt_template", "").replace("{{repo_name}}", repo_full) \
                                                            .replace("{{change_summary}}", change_summary) \
                                                            .replace("{{memory_context}}", memory)

            response = await litellm.acompletion(
                model=settings.LITELLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result_str = response.choices[0].message.content
            result = json.loads(result_str)

            # Apply updates (simplified - real version would diff and patch)
            for update in result.get("updated_files", []):
                path = update["path"]
                content = update["content"]
                try:
                    file = repo.get_contents(path)
                    repo.update_file(path, "docs: auto-update", content, file.sha)
                except:
                    repo.create_file(path, "docs: initial auto-update", content)

            logger.info(f"Docs updated for {repo_full} - {len(result.get('updated_files', []))} files")
            return result
        except Exception as e:
            logger.error(f"Docs update failed: {e}")
            return {"error": str(e)}
