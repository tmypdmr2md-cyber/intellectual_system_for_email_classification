import json
import re
from pathlib import Path
from typing import Any, Optional


class EmailParser:
    TEXT_EXTENSIONS = {".txt", ".eml", ".mail", ""}
    JSON_EXTENSIONS = {".json"}
    BINARY_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".docx", ".xlsx", ".bin", ".zip"}

    HEADER_MAP = {
        "from": "sender",
        "от кого": "sender",
        "ot kogo": "sender",
        "to": "recipients",
        "кому": "recipients",
        "komu": "recipients",
        "date": "received_at",
        "дата": "received_at",
        "data": "received_at",
        "subject": "subject",
        "тема": "subject",
        "tema": "subject",
    }

    def parse(self, path: Path) -> dict[str, Any]:
        file = Path(path)
        extension = file.suffix.lower()

        result = {
            "source_path": str(file),
            "filename": file.name,
            "extension": extension or None,
        }

        if not file.exists():
            return {
                **result,
                "status": "file_not_found",
                "is_garbage": True,
            }

        if extension in self.BINARY_EXTENSIONS:
            return {
                **result,
                "status": "binary_file",
                "is_garbage": True,
                "file_type": "binary",
            }

        if extension in self.JSON_EXTENSIONS:
            return self._parse_json(file, result)

        if extension in self.TEXT_EXTENSIONS:
            return self._parse_text(file, result)

        return {
            **result,
            "status": "unsupported_extension",
            "is_garbage": True,
            "file_type": "unknown",
        }

    def _parse_text(self, file: Path, result: dict[str, Any]) -> dict[str, Any]:
        text = file.read_text(encoding="utf-8", errors="ignore")

        if not text.strip():
            return {
                **result,
                "status": "empty_file",
                "is_garbage": True,
                "raw_text": text,
            }

        email = self._extract_fields(text)
        warnings = self._validate_missing(email)

        return {
            **result,
            "status": "parsed",
            "is_garbage": False,
            "file_type": "text",
            "email": email,
            "raw_text": text,
            "warnings": warnings,
        }

    def _parse_json(self, file: Path, result: dict[str, Any]) -> dict[str, Any]:
        text = file.read_text(encoding="utf-8", errors="ignore")

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {
                **result,
                "status": "broken_json",
                "is_garbage": True,
                "raw_text": text,
            }

        email = {
            "sender": self._parse_contact(data.get("from") or data.get("sender") or "unknown"),
            "recipients": data.get("to") or data.get("recipients") or [],
            "received_at": data.get("date") or data.get("received_at"),
            "subject": data.get("subject") or "Без темы",
            "body": data.get("body") or "",
            "attachments": data.get("attachments") or [],
            "ticket_id": data.get("ticket_id"),
            "error_code": data.get("error_code"),
        }

        return {
            **result,
            "status": "parsed",
            "is_garbage": False,
            "file_type": "json",
            "email": email,
            "raw_text": text,
            "warnings": self._validate_missing(email),
        }

    def _extract_fields(self, text: str) -> dict[str, Any]:
        headers = {}
        body_lines = []
        is_header_part = True

        for line in text.splitlines():
            clean_line = line.strip()

            if clean_line == "":
                is_header_part = False
                continue

            if is_header_part and ":" in clean_line:
                key, value = clean_line.split(":", 1)
                key = key.lower().strip()
                value = value.strip()

                field_name = self.HEADER_MAP.get(key)

                if field_name:
                    headers[field_name] = value
                    continue

            body_lines.append(line)

        body = "\n".join(body_lines).strip()
        return {
            "sender": self._parse_contact(headers.get("sender", "unknown")),
            "recipients": self._parse_recipients(headers.get("recipients", "")),
            "received_at": headers.get("received_at"),
            "subject": headers.get("subject") or "Без темы",
            "body": body,
            "attachments": self._find_attachments(text),
            "ticket_id": self._find_by_pattern(text, r"ID заявки:\s*(#[0-9]+)"),
            "error_code": self._find_by_pattern(text, r"Код ошибки:\s*(ERR_[0-9]+)"),
        }

    def _parse_contact(self, value: str) -> dict[str, Optional[str]]:
        match = re.search(r"(.+)?<(.+@.+)>", value)

        if match:
            name = match.group(1)
            return {
                "name": name.strip() if name else None,
                "email": match.group(2).strip(),
            }

        return {
            "name": None,
            "email": value.strip(),
        }

    def _parse_recipients(self, value: str) -> list[dict[str, Optional[str]]]:
        if not value:
            return []

        return [
            self._parse_contact(item.strip())
            for item in value.split(",")
            if item.strip()
        ]

    def _find_attachments(self, text: str) -> list[str]:
        attachments = []
        keywords = [
            "Вложение:",
            "Во вложении:",
            "Прикрепил:",
            "Файл:",
            "Attachment:",
            "Attached:",
            "Attached file:",
            "File:",
        ]

        for line in text.splitlines():
            clean_line = line.strip()
            lower_line = clean_line.lower()

            for keyword in keywords:
                lower_keyword = keyword.lower()

                if lower_line.startswith(lower_keyword):
                    filename = clean_line[len(keyword):].strip()
                    attachments.append(filename)

        return attachments

    def _find_by_pattern(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None

    def _validate_missing(self, email: dict[str, Any]) -> list[str]:
        warnings = []

        if email["sender"]["email"] == "unknown":
            warnings.append("missing_sender")

        if not email["recipients"]:
            warnings.append("missing_recipients")

        if not email["received_at"]:
            warnings.append("missing_date")

        if email["subject"] == "Без темы":
            warnings.append("missing_subject")

        if not email["body"]:
            warnings.append("missing_body")

        return warnings
