import asyncio
import json
import litellm
from pydantic import BaseModel, ValidationError, Field
from core.config import settings
from core.lancedb_client import query_memory
from core.github_client import get_github_client
from core.observability import traced_task, task_duration_seconds
from skills.pr_intelligence.skill import PRIntelligenceSkill
from skills.issue_triage.skill import IssueTriageSkill
from skills.test_generator.skill import TestGeneratorSkill
from skills.docs_updater.skill import DocsUpdaterSkill
from skills.dependency_updater.skill import DependencyUpdaterSkill
from skills.changelog_god.skill import ChangelogGodSkill
import structlog

logger = structlog.get_logger()

class TaskPlanItem(BaseModel):
    name: str = Field(..., description="Must be one of the allowed skill names")
    deps: list[str] = Field(default_factory=list, description="Names of prerequisite tasks")
    description: str = ""

class TaskPlan(BaseModel):
    tasks: list[TaskPlanItem]

class Task:
    def __init__(self, name: str, fn, deps: list[str] = None, priority: float = 0.0):
        self.name = name
        self.fn = fn
        self.deps = deps or []
        self.priority = priority
        self.result = None

class Planner:
    def __init__(self):
        self.skills = {
            "pr_intelligence": PRIntelligenceSkill(),
            "issue_triage": IssueTriageSkill(),
            "test_generator": TestGeneratorSkill(),
            "docs_updater": DocsUpdaterSkill(),
            "dependency_updater": DependencyUpdaterSkill(),
            "changelog_god": ChangelogGodSkill(),
        }
        self.allowed_task_names = list(self.skills.keys())

    async def generate_plan(self, payload: dict, event: str) -> list[Task]:
        repo_full = payload.get("repository", {}).get("full_name", "unknown")
        context = await query_memory(repo_full, f"Event: {event} context")
        allowed_str = ", ".join(self.allowed_task_names)

        prompt = f"""
You are an expert DevOps planner.
Generate a multi-step plan for event '{event}' in repo '{repo_full}'.
Context: {context[:2000]}

Rules:
- ONLY use these task names: {allowed_str}
- Each task must have a name from the list above
- deps must reference other task names in the same plan
- Prioritize high-risk or foundational tasks first
- Output valid JSON only, no extra text

Example output:
{{
  "tasks": [
    {{"name": "pr_intelligence", "deps": [], "description": "Review PR"}},
    {{"name": "test_generator", "deps": ["pr_intelligence"], "description": "Add tests"}}
  ]
}}
"""

        for attempt in range(3):
            try:
                response = await litellm.acompletion(
                    model=settings.LITELLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                raw = response.choices[0].message.content
                plan_data = json.loads(raw)
                validated = TaskPlan.model_validate(plan_data)

                tasks = []
                for item in validated.tasks:
                    if item.name not in self.allowed_task_names:
                        raise ValueError(f"Invalid task name: {item.name}")
                    skill = self.skills[item.name]
                    fn = skill.process if hasattr(skill, "process") else skill.run
                    tasks.append(Task(item.name, fn, item.deps, priority=0.0))  # priority calculated later

                # Sort by dependency depth (simple topological sort prep)
                tasks.sort(key=lambda t: len(t.deps), reverse=True)
                return tasks
            except (json.JSONDecodeError, ValidationError, ValueError) as e:
                logger.warning(f"Plan attempt {attempt+1} failed: {e}")
                prompt += "\nPrevious attempt had invalid JSON or unknown task names. Fix it."
        logger.error("Failed to generate valid plan after 3 attempts")
        return []

    async def execute_graph(self, tasks: list[Task], payload: dict):
        pending = {t.name: t for t in tasks}
        completed = {}

        while pending:
            progress = False
            for name, task in list(pending.items()):
                if all(dep in completed for dep in task.deps):
                    start_time = asyncio.get_event_loop().time()
                    try:
                        with traced_task(task.name):
                            task.result = await task.fn(payload)
                        duration = asyncio.get_event_loop().time() - start_time
                        task_duration_seconds.observe(duration)
                        completed[name] = task.result
                        del pending[name]
                        progress = True
                    except Exception as e:
                        logger.error(f"Task {name} failed: {e}")
                        # Could implement rollback here if needed
            if not progress and pending:
                logger.error("Deadlock detected in task graph")
                break
            await asyncio.sleep(0.01)  # yield

        return completed

    async def plan_and_execute(self, payload: dict, event: str, pr_diff: str = ""):
        repo_full = payload.get("repository", {}).get("full_name", "unknown")
        repo_path = f"{settings.DATA_DIR}/repos/{repo_full.replace('/', '_')}"

        # Inject impacted functions from diff if available
        if pr_diff:
            from core.pr_change_analyzer import get_changed_functions
            impacted = await get_changed_functions(pr_diff, repo_path)
            payload["impacted_functions"] = list(impacted)
        else:
            payload["impacted_functions"] = []

        tasks = await self.generate_plan(payload, event)
        if not tasks:
            logger.warning("Empty plan generated - skipping execution")
            return {}

        results = await self.execute_graph(tasks, payload)
        logger.info(f"Executed plan for {event} in {repo_full}: {len(results)} tasks completed")
        return results

planner = Planner()
