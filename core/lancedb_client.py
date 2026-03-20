import lancedb
from pathlib import Path
import litellm
from core.config import settings
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()

DB_PATH = Path(settings.DATA_DIR) / "lancedb"
DB_PATH.mkdir(parents=True, exist_ok=True)
db = lancedb.connect(str(DB_PATH))

def get_table(repo_name: str):
    table_name = repo_name.replace("/", "_").replace("-", "_")
    if table_name not in db.table_names():
        schema = {"text": "string", "vector": "float32[384]", "timestamp": "string"}
        db.create_table(table_name, schema=schema)
    return db.open_table(table_name)

async def summarize_text(text: str, max_len: int = 5000) -> str:
    if len(text) <= max_len:
        return text
    try:
        response = await litellm.acompletion(
            model=settings.LITELLM_MODEL,
            messages=[{"role": "user", "content": f"Summarize concisely:\n{text[:15000]}"}],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Summarization failed: {e}")
        return text[:max_len] + "... [truncated]"

async def generate_embedding(text: str) -> list[float]:
    try:
        resp = await litellm.aembedding(model=settings.LITELLM_MODEL, input=[text])
        return resp.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return [0.0] * 384  # fallback dimension

async def add_memory(repo_name: str, text: str):
    summary = await summarize_text(text)
    embedding = await generate_embedding(summary)
    table = get_table(repo_name)
    table.add([{
        "text": summary,
        "vector": embedding,
        "timestamp": datetime.utcnow().isoformat()
    }])
    logger.debug(f"Added memory entry to {repo_name} ({len(summary)} chars)")

async def query_memory(repo_name: str, query_text: str, limit: int = 6) -> str:
    embedding = await generate_embedding(query_text)
    table = get_table(repo_name)
    results = table.search(embedding).limit(limit).to_list()
    if not results:
        return ""
    return "\n\n".join([r["text"] for r in results])

async def cleanup_old_memory(repo_name: str, days: int = 30):
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    table = get_table(repo_name)
    try:
        table.delete(f"timestamp < '{cutoff}'")
        logger.info(f"Cleaned old memory entries for {repo_name} (older than {days} days)")
    except Exception as e:
        logger.warning(f"Memory cleanup failed for {repo_name}: {e}")
