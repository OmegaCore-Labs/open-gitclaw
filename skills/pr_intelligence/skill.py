import json
import litellm
import difflib
import unidiff
from core.config import settings
from core.lancedb_client import query_memory, add_memory
from core.github_client import get_github_client
import structlog

logger = structlog.get_logger()

class PRIntelligenceSkill:
    def __init__(self):
        self.metadata = SKILLS.get("pr_intelligence", {})

    async def process(self, payload: dict):
        try:
            repo_full = payload["repository"]["full_name"]
            pr_num = payload["pull_request"]["number"]

            gh = get_github_client(repo_full)
            repo = gh.get_repo(repo_full)
            pr = repo.get_pull(pr_num)

            diff_raw = httpx.get(pr.diff_url).text
            memory = await query_memory(repo_full, f"PR {pr_num} review context")
            await add_memory(repo_full, f"PR {pr_num} diff summary: {diff_raw[:2000]}")

            prompt = self.metadata.get("prompt_template", "").replace("{{pr_number}}", str(pr_num)) \
                                                            .replace("{{repo_name}}", repo_full) \
                                                            .replace("{{diff_summary}}", diff_raw[:8000]) \
                                                            .replace("{{memory_context}}", memory)

            response = await litellm.acompletion(
                model=settings.LITELLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result_str = response.choices[0].message.content
            result = json.loads(result_str)

            # Post review comment
            if "review_comment" in result:
                pr.create_review(body=result["review_comment"], event="COMMENT")

            # Apply patch if provided
            if "patch" in result and result["recommendation"] == "open_fix_pr":
                branch = f"claw-fix-{pr_num}"
                repo.create_git_ref(f"refs/heads/{branch}", pr.base.sha)

                # Parse patch with unidiff
                patch_set = unidiff.PatchSet(result["patch"])
                for patched_file in patch_set:
                    try:
                        file = repo.get_contents(patched_file.path, ref=branch)
                        original = file.decoded_content.decode()
                        patched = original  # apply patch logic (simplified here)
                        repo.update_file(
                            patched_file.path,
                            f"🦞 Auto-fix for PR #{pr_num}",
                            patched,
                            file.sha,
                            branch=branch
                        )
                    except Exception as e:
                        logger.warning(f"Patch apply failed for {patched_file.path}: {e}")

                fix_pr = repo.create_pull(
                    title=f"🦞 Auto-fix for #{pr_num}",
                    body=result["review_comment"],
                    head=branch,
                    base=pr.base.ref
                )
                logger.info(f"Opened auto-fix PR #{fix_pr.number}")

            # Auto-merge if safe
            if result["recommendation"] == "auto_merge":
                pr.merge(commit_title=f"🦞 Auto-merge PR #{pr_num}")

            logger.info(f"PR {pr_num} intelligence complete")
            return result
        except Exception as e:
            logger.error(f"PR intelligence failed: {e}")
            return {"error": str(e)}
