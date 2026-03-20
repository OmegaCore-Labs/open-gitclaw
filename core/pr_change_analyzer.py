from pathlib import Path
import asyncio
import structlog
from core.repo_graph import get_impacted_functions, file_functions

logger = structlog.get_logger()

async def get_changed_functions(pr_diff_text: str, repo_path: str) -> set[str]:
    changed_funcs = set()

    current_file = None
    for line in pr_diff_text.splitlines():
        line = line.strip()
        if line.startswith("diff --git"):
            parts = line.split()
            if len(parts) >= 3:
                file_path = parts[2].lstrip("a/").rstrip()
                current_file = Path(file_path).as_posix()
        elif line.startswith("@@") and current_file and current_file in file_functions:
            # For simplicity, mark all functions in changed file as potentially impacted
            changed_funcs.update(file_functions[current_file])

    if changed_funcs:
        impacted = await get_impacted_functions(list(changed_funcs))
        logger.info(f"Changed functions: {len(changed_funcs)}, Impacted: {len(impacted)}")
        return impacted
    return set()
