from sentence_transformers import SentenceTransformer

from src.core import config


class EmbeddingService:
    def __init__(self):
        self.model_name = config.EMBEDDING_MODEL_NAME
        self.model = SentenceTransformer(
            self.model_name,
            # local_files_only=True, # включить после того как у вас 
        )

    def build_text(self, email_json: dict) -> str:
        email = email_json.get("email") or {}

        subject = email.get("subject") or ""
        body = email.get("body") or ""

        return f"{subject}\n{body}".strip()

    def create_embedding(self, email_json: dict) -> list:
        text = self.build_text(email_json)

        embedding = self.model.encode(text)

        return embedding.tolist()
