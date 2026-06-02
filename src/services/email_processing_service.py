from sqlalchemy.orm import Session

from src.core import config
from src.core.classification.rule_based_classification import RuleBasedClassifier
from src.core.decision.decision_engine import DecisionEngine
from src.core.entities.entity_extractor import EntityExtractor
from src.core.llm.gigachat_client import GigaChatClient
from src.core.semantic_search.semantic_search_service import SemanticSearchService

from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.classification_repository import ClassificationRepository
from src.db.repositories.email_repository import EmailRepository
from src.db.repositories.embedding_repository import EmbeddingRepository


class EmailProcessingService:
    def __init__(self, db: Session):
        self.db = db

        self.email_repository = EmailRepository(db)
        self.category_repository = CategoryRepository(db)
        self.classification_repository = ClassificationRepository(db)
        self.embedding_repository = EmbeddingRepository(db)
        self.category_repository.ensure_default_categories()

        self.rule_classifier = RuleBasedClassifier()
        self.embedding_service = None
        self.semantic_search_service = SemanticSearchService()
        self.entity_extractor = EntityExtractor()
        self.decision_engine = DecisionEngine()
        self.gigachat_client = GigaChatClient()

    def process_next_emails(self, limit: int = None) -> dict:
        if limit is None:
            limit = config.PROCESSING_CONCURRENCY

        emails = self.email_repository.get_unprocessed_emails(limit=limit)

        results = []

        for email in emails:
            try:
                result = self.process_one_email(email)
                results.append(result)

            except Exception as error:
                self.email_repository.mark_failed(email)

                results.append(
                    {
                        "email_id": email.id,
                        "status": "failed",
                        "error": str(error),
                    }
                )

        return {
            "processed": len(results),
            "results": results,
        }

    def process_all_emails(self, batch_size: int = None) -> dict:
        if batch_size is None:
            batch_size = config.PROCESSING_CONCURRENCY

        total_processed = 0
        results = []

        while True:
            batch = self.process_next_emails(limit=batch_size)
            if batch["processed"] == 0:
                break

            total_processed += batch["processed"]
            results.extend(batch["results"])

        return {
            "processed": total_processed,
            "results": results,
        }

    def process_one_email(self, email) -> dict:
        self.email_repository.mark_processing(email)

        parsed_json = email.parsed_json

        rule_result = self.rule_classifier.classify(parsed_json)
        entities = self.entity_extractor.extract(parsed_json)

        embedding = None
        similar_emails = []

        final_decision = self.decision_engine.decide_pre_llm(
            rule_result=rule_result,
            similar_emails=similar_emails,
        )

        if not final_decision:
            embedding = self._embedding_service().create_embedding(parsed_json)

            stored_embeddings = self.embedding_repository.get_all_with_categories()

            similar_emails = self.semantic_search_service.find_similar(
                current_embedding=embedding,
                stored_embeddings=stored_embeddings,
            )

            final_decision = self.decision_engine.decide_pre_llm(
                rule_result=rule_result,
                similar_emails=similar_emails,
            )

        if not final_decision:
            existing_categories = self.category_repository.list_names()
            llm_result = self.gigachat_client.suggest_category(
                email_json=parsed_json,
                entities=entities,
                similar_emails=similar_emails,
                existing_categories=existing_categories,
            )

            final_decision = self.decision_engine.decide(
                rule_result=rule_result,
                similar_emails=similar_emails,
                llm_result=llm_result,
            )

        final_decision = self._with_text_defaults(final_decision, parsed_json)

        category = self._get_category(final_decision)

        self.classification_repository.create(
            email_id=email.id,
            category_id=category.id,
            confidence=final_decision["confidence"],
            method=final_decision["method"],
            reason=final_decision["reason"],
            entities_json=entities,
            similar_emails_json=similar_emails,
            corrected_subject=final_decision["corrected_subject"],
            corrected_body=final_decision["corrected_body"],
            grammar_issues_found=final_decision["grammar_issues_found"],
            grammar_corrections=final_decision["grammar_corrections"],
        )

        if embedding is None:
            embedding = self._embedding_service().create_embedding(parsed_json)

        self.embedding_repository.create(
            email_id=email.id,
            embedding=embedding,
            model_name=self._embedding_service().model_name,
        )

        self.email_repository.mark_classified(email)

        return {
            "email_id": email.id,
            "filename": email.filename,
            "category": category.name,
            "confidence": final_decision["confidence"],
            "method": final_decision["method"],
            "reason": final_decision["reason"],
            "entities": entities,
            "similar_emails": similar_emails,
            "corrected_subject": final_decision["corrected_subject"],
            "corrected_body": final_decision["corrected_body"],
            "grammar_issues_found": final_decision["grammar_issues_found"],
            "grammar_corrections": final_decision["grammar_corrections"],
        }

    def _with_text_defaults(self, decision: dict, parsed_json: dict) -> dict:
        email = parsed_json.get("email") or {}
        subject = email.get("subject") or ""
        body = email.get("body") or ""

        decision["corrected_subject"] = decision.get("corrected_subject")
        if decision["corrected_subject"] is None:
            decision["corrected_subject"] = subject

        decision["corrected_body"] = decision.get("corrected_body")
        if decision["corrected_body"] is None:
            decision["corrected_body"] = body

        decision["grammar_issues_found"] = bool(decision.get("grammar_issues_found", False))

        grammar_corrections = decision.get("grammar_corrections")
        if not isinstance(grammar_corrections, list):
            grammar_corrections = []
        decision["grammar_corrections"] = grammar_corrections

        return decision

    def _get_category(self, decision: dict):
        category_name = decision.get("category") or "unknown"

        if decision.get("is_new_category"):
            return self.category_repository.get_or_create(
                name=category_name,
                title=decision.get("new_category_title") or category_name,
                description=decision.get("new_category_description") or "",
                is_default=False,
                created_by="llm_gigachat",
            )

        default_category = self._default_category(category_name)

        return self.category_repository.get_or_create(
            name=category_name,
            title=default_category.get("title", category_name),
            description=default_category.get("description", ""),
            is_default=bool(default_category),
            created_by=decision.get("method", "system"),
        )

    def _default_category(self, name: str) -> dict:
        for category in config.DEFAULT_CATEGORIES:
            if category["name"] == name:
                return category

        return {}

    def _embedding_service(self):
        if self.embedding_service is None:
            from src.core.embeddings.embedding_service import EmbeddingService

            self.embedding_service = EmbeddingService()

        return self.embedding_service
