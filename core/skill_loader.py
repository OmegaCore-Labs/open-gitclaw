from pathlib import Path
import yaml
import structlog
from typing import Dict, Any

logger = structlog.get_logger()

SKILLS: Dict[str, Dict[str, Any]] = {}

def load_all_skills():
    skills_dir = Path(__file__).parent.parent / "skills"
    if not skills_dir.is_dir():
        logger.warning("No skills directory found")
        return

    for skill_folder in skills_dir.iterdir():
        if not skill_folder.is_dir():
            continue
        soul_path = skill_folder / "SOUL.md"
        if not soul_path.is_file():
            continue

        try:
            content = soul_path.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                frontmatter_str = parts[1].strip() if len(parts) > 1 else ""
                prompt_template = parts[2].strip() if len(parts) > 2 else ""
            else:
                frontmatter_str = ""
                prompt_template = content.strip()

            metadata = yaml.safe_load(frontmatter_str) or {}
            metadata["prompt_template"] = prompt_template
            metadata["version"] = metadata.get("version", "1.0.0")
            metadata["folder"] = skill_folder.name

            SKILLS[skill_folder.name] = metadata
            logger.debug(f"Loaded skill: {skill_folder.name} v{metadata['version']}")
        except Exception as e:
            logger.error(f"Failed to load skill {skill_folder.name}: {e}")

    logger.info(f"Loaded {len(SKILLS)} skills: {list(SKILLS.keys())}")

# Run on import
load_all_skills()
