import json
import tempfile
import unittest
from pathlib import Path
from typing import Union

from src.core.parser.email_parser import EmailParser


class EmailParserTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = EmailParser()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_file(self, name: str, content: Union[str, bytes]) -> Path:
        path = self.root / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def test_parse_english_text_email(self):
        path = self.write_file(
            "mail.txt",
            "\n".join(
                [
                    "From: Ivan Petrov <ivan@example.com>",
                    "To: it-support@example.com",
                    "Date: 2025-04-01 10:15",
                    "Subject: Не работает VPN",
                    "",
                    "Здравствуйте.",
                    "Не могу войти в VPN.",
                ]
            ),
        )

        parsed = self.parser.parse(path)

        self.assertEqual(parsed["status"], "parsed")
        self.assertFalse(parsed["is_garbage"])
        self.assertEqual(parsed["email"]["sender"]["name"], "Ivan Petrov")
        self.assertEqual(parsed["email"]["sender"]["email"], "ivan@example.com")
        self.assertEqual(parsed["email"]["recipients"][0]["email"], "it-support@example.com")
        self.assertEqual(parsed["email"]["received_at"], "2025-04-01 10:15")
        self.assertEqual(parsed["email"]["subject"], "Не работает VPN")
        self.assertIn("Не могу войти", parsed["email"]["body"])
        self.assertEqual(parsed["warnings"], [])

    def test_parse_russian_text_email_with_attachment_and_ticket(self):
        path = self.write_file(
            "mail.txt",
            "\n".join(
                [
                    "От кого: Мария <maria@example.com>",
                    "Кому: it-support@example.com",
                    "Дата: 01.04.2025 10:15",
                    "Тема: Ошибка в Excel",
                    "",
                    "Код ошибки: ERR_500",
                    "Файл: error_log.txt",
                    "ID заявки: #12345",
                ]
            ),
        )

        parsed = self.parser.parse(path)

        self.assertEqual(parsed["email"]["subject"], "Ошибка в Excel")
        self.assertEqual(parsed["email"]["attachments"], ["error_log.txt"])
        self.assertEqual(parsed["email"]["ticket_id"], "#12345")
        self.assertEqual(parsed["email"]["error_code"], "ERR_500")

    def test_parse_transliterated_headers(self):
        path = self.write_file(
            "mail",
            "\n".join(
                [
                    "Ot kogo: a.fedorova@company.ru <a.fedorova@company.ru>",
                    "Komu: it-support@company.ru",
                    "Data: 25.03.2025 17:46",
                    "Tema: Izmenenie grafika raboty",
                    "",
                    "Napravlyayu bolnichnyy list.",
                ]
            ),
        )

        parsed = self.parser.parse(path)

        self.assertEqual(parsed["extension"], None)
        self.assertEqual(parsed["email"]["subject"], "Izmenenie grafika raboty")
        self.assertEqual(parsed["email"]["received_at"], "25.03.2025 17:46")
        self.assertIn("bolnichnyy", parsed["email"]["body"])

    def test_parse_contact_without_display_name(self):
        contact = self.parser._parse_contact("<user@example.com>")

        self.assertIsNone(contact["name"])
        self.assertEqual(contact["email"], "user@example.com")

    def test_empty_file_is_garbage(self):
        path = self.write_file("empty.txt", "")

        parsed = self.parser.parse(path)

        self.assertEqual(parsed["status"], "empty_file")
        self.assertTrue(parsed["is_garbage"])

    def test_binary_extension_is_garbage_without_reading_as_text(self):
        path = self.write_file("mail.bin", b"\x00\x01\x02")

        parsed = self.parser.parse(path)

        self.assertEqual(parsed["status"], "binary_file")
        self.assertTrue(parsed["is_garbage"])
        self.assertEqual(parsed["file_type"], "binary")

    def test_broken_json_is_garbage(self):
        path = self.write_file("mail.json", '{"from": "test@example.com", "body":')

        parsed = self.parser.parse(path)

        self.assertEqual(parsed["status"], "broken_json")
        self.assertTrue(parsed["is_garbage"])

    def test_valid_json_is_parsed(self):
        path = self.write_file(
            "mail.json",
            json.dumps(
                {
                    "from": "test@example.com",
                    "to": [{"name": None, "email": "it-support@example.com"}],
                    "date": "2025-04-01",
                    "subject": "Запрос доступа",
                    "body": "Нужен доступ к GitLab",
                },
                ensure_ascii=False,
            ),
        )

        parsed = self.parser.parse(path)

        self.assertEqual(parsed["status"], "parsed")
        self.assertEqual(parsed["file_type"], "json")
        self.assertEqual(parsed["email"]["subject"], "Запрос доступа")
        self.assertEqual(parsed["warnings"], [])


if __name__ == "__main__":
    unittest.main()
