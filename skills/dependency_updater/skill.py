import json
import litellm
from core.config import settings
from core.lancedb_client import query_memory, add_memory
from core.github_client import get_github_client
import structlog

logger = structlog.get_logger()

class DependencyUpdaterSkill:
    def __init__(self):
        self.metadata = SKILLS.get("dependency_updater", {})

    async def run(self, payload: dict = None):
        try:
            repo_full = payload.get("repository", {}).get("full_name", "unknown") if payload else "default"
            gh = get_github_client(repo_full)
            repo = gh.get_repo(repo_full)

            memory = await query_memory(repo_full, "Dependency update context")
            await add_memory(repo_full, "Dependency scan initiated")

            prompt = self.metadata.get("prompt_template", "").replace("{{repo_name}}", repo_full) \
                                                            .replace("{{memory_context}}", memory)

            response = await litellm.acompletion(
                model=settings.LITELLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result_str = response.choices[0].message.content
            result = json.loads(result_str)

            if "updates" in result and result["updates"]:
                branch = "chore-deps-update"
                repo.create_git_ref(f"refs/heads/{branch}", repo.default_branch)

                # For simplicity, assume requirements.txt update
                # Real impl would parse lockfiles, use dependabot logic, etc.
                updated_content = "# Updated dependencies\n" + "\n".join(
                    f"{u['package']}=={u['target']} # was {u['current']}" for u in result["updates"]
                )

                try:
                    req_file = repo.get_contents("requirements.txt", ref=branch)
                    repo.update_file(
                        "requirements.txt",
                        result["pr_title"],
                        updated_content,
                        req_file.sha,
                        branch=branch
                    )
                except:
                    repo.create_file(
                        "requirements.txt",
                        result["pr_title"],
                        updated_content,
                        branch=branch
                    )

                pr = repo.create_pull(
                    title=result["pr_title"],
                    body=result["pr_body"],
                    head=branch,
                    base=repo.default_branch
                )
                logger.info(f"Opened dependency update PR #{pr.number} for {repo_full}")

            return result
        except Exception as e:
            logger.error(f"Dependency update failed: {e}")
            return {"error": str(e)}
