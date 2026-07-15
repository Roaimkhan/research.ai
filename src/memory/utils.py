from fastembed import TextEmbedding

# Initialize the model (it downloads a tiny file, ~30MB)
model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def embed_text(text: str) -> list[float]:
    # fastembed returns a generator, so we grab the first result
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()