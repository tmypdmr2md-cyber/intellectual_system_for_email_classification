import unittest

from src.core.llm.gigachat_client import GigaChatClient


class GigaChatClientTestCase(unittest.TestCase):
    def test_fallback_when_credentials_are_missing(self):
        client = GigaChatClient()
        client.credentials = ""

        result = client.suggest_category(
            email_json={"email": {"subject": "Тест", "body": "Текст"}},
            entities={},
            similar_emails=[],
            existing_categories=["unknown"],
        )

        self.assertEqual(result["category"], "unknown")
        self.assertEqual(result["method"], "llm_unavailable")

    def test_extract_json_from_markdown_block(self):
        client = GigaChatClient()

        result = client._extract_json(
            '```json\n{"category":"meeting","confidence":0.8,"reason":"demo"}\n```'
        )

        self.assertEqual(result["category"], "meeting")
        self.assertEqual(result["confidence"], 0.8)

    def test_normalize_result_rejects_unknown_category_name(self):
        client = GigaChatClient()

        result = client._normalize_result(
            {
                "category": "new_category",
                "confidence": 2.0,
                "reason": "bad category",
            },
            existing_categories=["unknown", "meeting"],
        )

        self.assertEqual(result["category"], "unknown")
        self.assertEqual(result["confidence"], 1.0)
        self.assertEqual(result["method"], "llm_gigachat")

    def test_normalize_result_maps_known_category_alias(self):
        client = GigaChatClient()

        result = client._normalize_result(
            {
                "category": "corporate_news",
                "confidence": 0.82,
                "reason": "company digest",
            },
            existing_categories=["unknown", "newsletter"],
        )

        self.assertEqual(result["category"], "newsletter")
        self.assertEqual(result["confidence"], 0.82)

    def test_suggest_category_uses_chat_response_without_network_in_test(self):
        client = GigaChatClient()
        client.credentials = "fake"
        client._chat = lambda prompt: (
            '{"category":"meeting","confidence":0.73,"reason":"mentions meeting"}'
        )

        result = client.suggest_category(
            email_json={"email": {"subject": "Созвон", "body": "Нужно обсудить статус"}},
            entities={},
            similar_emails=[],
            existing_categories=["unknown", "meeting"],
        )

        self.assertEqual(result["category"], "meeting")
        self.assertEqual(result["confidence"], 0.73)
        self.assertEqual(result["method"], "llm_gigachat")
        self.assertEqual(result["corrected_subject"], "Созвон")
        self.assertEqual(result["corrected_body"], "Нужно обсудить статус")

    def test_normalize_result_keeps_grammar_fields(self):
        client = GigaChatClient()

        result = client._normalize_result(
            {
                "category": "meeting",
                "confidence": 0.8,
                "reason": "meeting",
                "corrected_subject": "Созвон",
                "corrected_body": "Нужно обсудить статус.",
                "grammar_issues_found": True,
                "grammar_corrections": [
                    {
                        "original": "статус",
                        "corrected": "статус.",
                        "type": "punctuation",
                        "explanation": "Добавлена точка",
                    }
                ],
            },
            existing_categories=["unknown", "meeting"],
        )

        self.assertTrue(result["grammar_issues_found"])
        self.assertEqual(result["grammar_corrections"][0]["type"], "punctuation")


if __name__ == "__main__":
    unittest.main()
