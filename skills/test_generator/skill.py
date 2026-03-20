import json
import litellm
import subprocess
from core.config import settings
from core.lancedb_client import query_memory, add_memory
from core.github_client import get_github_client
import structlog

logger = structlog.get_logger()

class TestGeneratorSkill:
    def __init__(self):
        self.metadata = SKILLS.get("test_generator", {})

    async def process(self, payload: dict):
        try:
            repo_full = payload.get("repository", {}).get("full_name", "unknown")
            change_context = payload.get("change_context", "Recent PR changes")

            gh = get_github_client(repo_full)
            repo = gh.get_repo(repo_full)

            memory = await query_memory(repo_full, "Test generation context")
            await add_memory(repo_full, f"Test gen for: {change_context[:500]}")

            prompt = self.metadata.get("prompt_template", "").replace("{{repo_name}}", repo_full) \
                                                            .replace("{{change_context}}", change_context) \
                                                            .replace("{{memory_context}}", memory)

            response = await litellm.acompletion(
                model=settings.LITELLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result_str = response.choices[0].message.content
            result = json.loads(result_str)

            # Write tests to temp file and run in sandbox (simplified)
            test_content = result["test_content"]
            test_path = "tests/test_generated.py"
            with open(test_path, "w") as f:
                f.write(test_content)

            try:
                subprocess.run(["pytest", test_path], check=True, capture_output=True)
                logger.info("Generated tests passed sandbox run")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Generated tests failed: {e.stderr.decode()}")
                return {"error": "Tests failed in sandbox"}

            # Open PR with tests
            branch = "chore/add-tests"
            repo.create_git_ref(f"refs/heads/{branch}", repo.default_branch)
            repo.create_file(test_path, "test: auto-generated coverage", test_content, branch=branch)
            pr = repo.create_pull(
                title="test: auto-generated coverage improvements",
                body=f"Coverage gain: ~{result['coverage_gain']}%",
                head=branch,
                base=repo.default_branch
            )
            logger.info(f"Opened test PR #{pr.number}")

            return result
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return {"error": str(e)}
