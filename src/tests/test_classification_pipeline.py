import unittest

from src.core.classification.rule_based_classification import RuleBasedClassifier
from src.core.decision.decision_engine import DecisionEngine
from src.core.entities.entity_extractor import EntityExtractor
from src.core.semantic_search.semantic_search_service import SemanticSearchService


class RuleBasedClassifierTestCase(unittest.TestCase):
    def setUp(self):
        self.classifier = RuleBasedClassifier()

    def test_classifies_access_request(self):
        result = self.classifier.classify(
            {
                "email": {
                    "subject": "Запрос доступа к VPN",
                    "body": "Нужны права для нового сотрудника.",
                    "sender": {"email": "user@example.com"},
                    "attachments": [],
                }
            }
        )

        self.assertEqual(result["category"], "access_request")
        self.assertGreaterEqual(result["confidence"], 0.5)
        self.assertLess(result["confidence"], 0.85)

    def test_classifies_garbage_from_parser_flag(self):
        result = self.classifier.classify(
            {
                "status": "binary_file",
                "is_garbage": True,
            }
        )

        self.assertEqual(result["category"], "garbage")
        self.assertEqual(result["confidence"], 1.0)

    def test_spam_has_priority_when_keywords_match(self):
        result = self.classifier.classify(
            {
                "email": {
                    "subject": "Срочно подтвердите личность",
                    "body": "Введите данные банковской карты для получения приза.",
                    "sender": {"email": "fake@example.com"},
                    "attachments": [],
                }
            }
        )

        self.assertEqual(result["category"], "spam")

    def test_classifies_monitoring_alert_before_urgent(self):
        result = self.classifier.classify(
            {
                "email": {
                    "subject": "[CRITICAL] Disk usage > 80% на prod",
                    "body": (
                        "Автоматическое уведомление от системы мониторинга.\n"
                        "Сервис: Auth Service\n"
                        "Статус: CRITICAL\n"
                        "Метрика: CPU usage 80%\n"
                        "Время: 2026-05-28 19:58"
                    ),
                }
            }
        )

        self.assertEqual(result["category"], "monitoring_alert")
        self.assertGreaterEqual(result["confidence"], 0.85)


class DecisionEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()

    def test_prefers_confident_rule_based_result(self):
        result = self.engine.decide(
            rule_result={
                "category": "incident",
                "confidence": 0.9,
                "reason": "Matched keywords",
            },
            similar_emails=[],
            llm_result={"category": "unknown", "confidence": 0.1, "method": "llm", "reason": "fallback"},
        )

        self.assertEqual(result["category"], "incident")
        self.assertEqual(result["method"], "rule_based")

    def test_uses_llm_when_rule_and_semantic_are_weak(self):
        result = self.engine.decide(
            rule_result={
                "category": "unknown",
                "confidence": 0.0,
                "reason": "No rule matched",
            },
            similar_emails=[],
            llm_result={
                "category": "meeting",
                "confidence": 0.72,
                "method": "llm_gigachat",
                "reason": "Meeting text",
            },
        )

        self.assertEqual(result["category"], "meeting")
        self.assertEqual(result["method"], "llm_gigachat")

    def test_semantic_search_can_raise_confidence(self):
        result = self.engine.decide(
            rule_result={
                "category": "unknown",
                "confidence": 0.0,
                "reason": "No rule matched",
            },
            similar_emails=[{"email_id": 10, "similarity": 0.91, "category": "meeting"}],
        )

        self.assertEqual(result["method"], "semantic_search")
        self.assertEqual(result["confidence"], 0.91)
        self.assertEqual(result["category"], "meeting")

    def test_semantic_search_skips_unknown_category(self):
        result = self.engine.decide(
            rule_result={
                "category": "unknown",
                "confidence": 0.0,
                "reason": "No rule matched",
            },
            similar_emails=[
                {"email_id": 10, "similarity": 0.95, "category": "unknown"},
                {"email_id": 11, "similarity": 0.88, "category": "meeting"},
            ],
        )

        self.assertEqual(result["method"], "semantic_search")
        self.assertEqual(result["category"], "meeting")


class EntityAndSemanticSearchTestCase(unittest.TestCase):
    def test_extracts_systems_attachments_and_error_code(self):
        result = EntityExtractor().extract(
            {
                "email": {
                    "subject": "Не работает VPN",
                    "body": "Код ошибки ERR_500. Вложение error_log.txt",
                    "error_code": "ERR_500",
                    "attachments": ["error_log.txt"],
                }
            }
        )

        self.assertIn("vpn", result["systems"])
        self.assertEqual(result["error_code"], "ERR_500")
        self.assertTrue(result["has_attachments"])

    def test_cosine_similarity(self):
        service = SemanticSearchService()

        self.assertAlmostEqual(service.cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertEqual(service.cosine_similarity([0, 0], [1, 0]), 0.0)


if __name__ == "__main__":
    unittest.main()
