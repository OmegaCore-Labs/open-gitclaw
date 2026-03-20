import json
import litellm
from core.config import settings
from core.lancedb_client import query_memory, add_memory
from core.github_client import get_github_client
import structlog

logger = structlog.get_logger()

class IssueTriageSkill:
    def __init__(self):
        self.metadata = SKILLS.get("issue_triage", {})

    async def process(self, payload: dict):
        try:
            repo_full = payload.get("repository", {}).get("full_name", "unknown")
            issue_num = payload.get("issue", {}).get("number")
            issue_title = payload.get("issue", {}).get("title", "")
            issue_body = payload.get("issue", {}).get("body", "")

            gh = get_github_client(repo_full)
            repo = gh.get_repo(repo_full)
            issue = repo.get_issue(issue_num)

            memory = await query_memory(repo_full, f"Issue triage: {issue_title}")
            await add_memory(repo_full, f"Issue {issue_num}: {issue_title}\n{issue_body[:500]}")

            prompt = self.metadata.get("prompt_template", "").replace("{{repo_name}}", repo_full) \
                                                            .replace("{{memory_context}}", memory) \
                                                            .replace("{{issue_title}}", issue_title) \
                                                            .replace("{{issue_body}}", issue_body)

            response = await litellm.acompletion(
                model=settings.LITELLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result_str = response.choices[0].message.content
            result = json.loads(result_str)

            # Apply labels
            if "labels" in result:
                issue.add_to_labels(*result["labels"])

            # Post reply if provided
            if "reply" in result and result["reply"]:
                issue.create_comment(result["reply"])

            # Close if instructed
            if result.get("action") == "close":
                issue.edit(state="closed")

            # Open fix PR if instructed
            if result.get("action") == "open_fix_pr" and "fix_plan" in result:
                branch = f"fix-issue-{issue_num}"
                repo.create_git_ref(f"refs/heads/{branch}", repo.default_branch)
                # Simplified - real impl would generate code from plan
                repo.create_file("fix.py", f"Fix for issue #{issue_num}", "# TODO: implement", branch=branch)
                pr = repo.create_pull(
                    title=f"Fix for issue #{issue_num}",
                    body=result["fix_plan"],
                    head=branch,
                    base=repo.default_branch
                )
                logger.info(f"Opened fix PR #{pr.number} for issue {issue_num}")

            logger.info(f"Issue {issue_num} triaged in {repo_full}")
            return result
        except Exception as e:
            logger.error(f"Issue triage failed: {e}")
            return {"error": str(e)}
