from fastembed import TextEmbedding
import time

from src.logging import record_embedding_call, spawn_background_task, get_logger

# Initialize the model (it downloads a tiny file, ~30MB)
model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
logger = get_logger(__name__)

def embed_text(text: str) -> list[float]:
    started_at = time.perf_counter()
    embeddings = list(model.embed([text]))
    record_embedding_call(duration_ms=int((time.perf_counter() - started_at) * 1000))
    logger.info(
        "Embedding generated",
        extra={"text_length": len(text), "word_count": len(text.split())},
    )
    return embeddings[0].tolist()


def fire_and_forget(func, state):
    spawn_background_task(func, state, name=getattr(func, "__name__", "background-task"))