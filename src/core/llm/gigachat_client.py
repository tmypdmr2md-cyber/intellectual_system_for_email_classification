import json
import logging
import re
import ssl
import time
import uuid
from typing import Any, Optional
from urllib import error, parse, request

from src.core import config

logger = logging.getLogger(__name__)


class GigaChatClient:
    def __init__(self):
        self.credentials = config.GIGACHAT_CREDENTIALS
        self.scope = config.GIGACHAT_SCOPE
        self.model = config.GIGACHAT_MODEL
        self.auth_url = config.GIGACHAT_AUTH_URL
        self.chat_url = config.GIGACHAT_CHAT_URL
        self.timeout = config.GIGACHAT_TIMEOUT
        self.verify_ssl = config.GIGACHAT_VERIFY_SSL

        self._access_token: Optional[str] = None
        self._token_expires_at = 0.0

        logger.info(
            "GigaChatClient initialized: model=%s scope=%s auth_url=%s chat_url=%s verify_ssl=%s credentials_configured=%s",
            self.model,
            self.scope,
            self.auth_url,
            self.chat_url,
            self.verify_ssl,
            bool(self.credentials),
        )

    def suggest_category(
        self,
        email_json: dict,
        entities: dict,
        similar_emails: list,
        existing_categories: list,
    ) -> dict:
        logger.info("GigaChat category suggestion started")
        logger.debug("GigaChat input email_json=%s", email_json)
        logger.debug("GigaChat input entities=%s", entities)
        logger.debug("GigaChat input similar_emails=%s", similar_emails)
        logger.debug("GigaChat input existing_categories=%s", existing_categories)

        if not self.credentials:
            logger.warning("GigaChat credentials are not configured")
            return self._fallback_result(
                "GigaChat credentials are not configured",
                email_json=email_json,
            )

        prompt = self._build_prompt(
            email_json=email_json,
            entities=entities,
            similar_emails=similar_emails,
            existing_categories=existing_categories,
        )
        logger.debug("GigaChat prompt=%s", prompt)

        try:
            content = self._chat(prompt)
            logger.debug("GigaChat raw content=%s", content)

            try:
                parsed = self._extract_json(content)
            except Exception as parse_error:
                logger.warning("GigaChat returned invalid JSON, trying repair: %s", parse_error)
                repaired_content = self._repair_json_with_gigachat(content)
                logger.debug("GigaChat repaired raw content=%s", repaired_content)
                parsed = self._extract_json(repaired_content)

            logger.debug("GigaChat parsed JSON=%s", parsed)
            if not isinstance(parsed, dict):
                return self._fallback_result(
                    "GigaChat returned JSON that is not an object",
                    email_json=email_json,
                )
        except Exception as exc:
            logger.exception("GigaChat request failed")
            return self._fallback_result(
                f"GigaChat request failed: {exc}",
                email_json=email_json,
            )

        result = self._normalize_result(parsed, existing_categories, email_json)
        logger.info(
            "GigaChat normalized result: category=%s confidence=%s method=%s reason=%s",
            result.get("category"),
            result.get("confidence"),
            result.get("method"),
            result.get("reason"),
        )

        return result

    def _chat(self, prompt: str) -> str:
        logger.info("GigaChat chat request started")
        token = self._get_access_token()

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты классифицируешь входящие письма IT поддержки. "
                        "Отвечай только валидным JSON без markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.0,
            "max_tokens": 4096,
            "stream": False,
            "response_format": {"type": "json_object"},
        }

        response = self._post_json(
            url=self.chat_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            payload=payload,
        )
        logger.debug("GigaChat chat response=%s", response)

        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError("GigaChat returned no choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content:
            raise RuntimeError("GigaChat returned empty content")

        return content

    def _repair_json_with_gigachat(self, broken_content: str) -> str:
        logger.info("GigaChat JSON repair request started")

        repair_prompt = (
            "Ниже текст, который должен быть JSON, но он синтаксически сломан. "
            "Исправь только JSON-синтаксис: экранируй кавычки внутри строк, "
            "экранируй переносы строк как \\n, добавь пропущенные запятые, если нужно. "
            "Не меняй значения полей, не добавляй новые поля и не удаляй поля. "
            "Верни только валидный JSON без markdown и без пояснений.\n\n"
            f"BROKEN_JSON:\n{broken_content}"
        )

        return self._chat(repair_prompt)

    def _get_access_token(self) -> str:
        logger.info("GigaChat access token requested")

        if self._access_token and time.time() < self._token_expires_at - 60:
            logger.info("Using cached GigaChat access token")
            return self._access_token

        body = parse.urlencode({"scope": self.scope}).encode("utf-8")
        req = request.Request(
            self.auth_url,
            data=body,
            headers={
                "Authorization": f"Basic {self.credentials}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )

        logger.info("Requesting new GigaChat access token from %s", self.auth_url)

        with request.urlopen(req, timeout=self.timeout, context=self._ssl_context()) as resp:
            raw_body = resp.read().decode("utf-8")
            logger.debug("GigaChat OAuth raw response=%s", raw_body)
            data = json.loads(raw_body)

        token = data.get("access_token")
        if not token:
            raise RuntimeError("OAuth response does not contain access_token")

        self._access_token = token
        expires_at = data.get("expires_at")
        if expires_at:
            self._token_expires_at = int(expires_at) / 1000
        else:
            self._token_expires_at = time.time() + 25 * 60

        logger.info("GigaChat access token received; expires_at=%s", self._token_expires_at)

        return token

    def _post_json(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict:
        logger.info("POST JSON request started: url=%s", url)
        logger.debug("POST JSON payload=%s", payload)

        req = request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout, context=self._ssl_context()) as resp:
                status_code = getattr(resp, "status", None)
                raw_body = resp.read().decode("utf-8")
                logger.info("POST JSON response received: url=%s status=%s", url, status_code)
                logger.debug("POST JSON raw response=%s", raw_body)
                return json.loads(raw_body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            logger.error("POST JSON HTTP error: url=%s code=%s body=%s", url, exc.code, body)
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except Exception:
            logger.exception("POST JSON request failed: url=%s", url)
            raise

    def _ssl_context(self):
        if self.verify_ssl:
            return None
        return ssl._create_unverified_context()

    def _build_prompt(
        self,
        email_json: dict,
        entities: dict,
        similar_emails: list,
        existing_categories: list,
    ) -> str:
        compact_email = email_json.get("email") or {}
        payload = {
            "allowed_categories": existing_categories,
            "email": {
                "subject": compact_email.get("subject"),
                "sender": compact_email.get("sender"),
                "body": (compact_email.get("body") or "")[:3000],
                "attachments": compact_email.get("attachments") or [],
            },
            "entities": entities,
            "similar_emails": similar_emails[:5],
        }

        logger.debug("GigaChat prompt payload=%s", payload)

        return (
            "Ты классифицируешь входящие письма IT поддержки и корпоративной коммуникации, "
            "а также аккуратно проверяешь тему и тело письма на грамматические, орфографические, "
            "пунктуационные и стилистические ошибки.\n\n"
            "Важные правила:\n"
            "1. Сначала выбери наиболее подходящую категорию из allowed_categories, "
            "если письмо подходит под одну из текущих категорий.\n"
            "2. Если письмо не подходит ни под одну текущую категорию, предложи новую категорию: "
            "is_new_category=true, category=машинное_имя_категории, new_category_title и "
            "new_category_description должны быть заполнены.\n"
            "3. Рассматривай все типы писем: запросы доступа, встречи, документы, уведомления, "
            "корпоративные новости, кадровые сообщения, изменения политик, инциденты, ошибки и другие темы.\n"
            "4. Не возвращай unknown только потому, что в письме нет ошибки, сбоя или технической проблемы.\n"
            "5. Если письмо является информационным дайджестом, корпоративной новостью, уведомлением "
            "или объявлением, выбери ближайшую подходящую категорию из allowed_categories.\n"
            "6. Проверяй subject и body. Исправляй ошибки без изменения смысла, без добавления фактов "
            "и без свободного переписывания.\n"
            "7. Не искажай имена сервисов, email-адреса, номера заявок, названия систем, логи, коды ошибок "
            "и технические термины.\n"
            "8. Если ошибок нет, верни исходные subject и body в corrected_subject и corrected_body.\n"
            "9. confidence должен быть числом от 0 до 1.\n"
            "10. Ответ должен быть только валидным JSON: без markdown, без ```json, без текста вне JSON.\n"
            "11. Не используй реальные переносы строк внутри строковых значений JSON. "
            "Если внутри corrected_body или reason нужен перенос строки, экранируй его как \\n.\n"
            "12. Все кавычки внутри строк экранируй как \\\".\n"
            "13. Не используй кавычки-ёлочки, обычные кавычки внутри текста и markdown. "
            "Если слово нужно выделить, используй апострофы или не выделяй его никак.\n"
            "14. Перед ответом мысленно проверь, что результат можно распарсить через json.loads().\n\n"
            "Верни строго JSON без markdown по схеме:\n"
            "{"
            '"category":"category_name",'
            '"confidence":0.82,'
            '"reason":"краткое объяснение выбора категории",'
            '"is_new_category":false,'
            '"new_category_title":"",'
            '"new_category_description":"",'
            '"corrected_subject":"исправленная тема письма",'
            '"corrected_body":"исправленное тело письма",'
            '"grammar_issues_found":false,'
            '"grammar_corrections":['
            "{"
            '"original":"исходный фрагмент",'
            '"corrected":"исправленный фрагмент",'
            '"type":"grammar|spelling|punctuation|style",'
            '"explanation":"краткое объяснение исправления"'
            "}"
            "]"
            "}\n\n"
            f"Данные:\n{json.dumps(payload, ensure_ascii=False)}"
        )

    def _extract_json(self, content: str) -> dict:
        logger.debug("Extracting JSON from GigaChat content")
        stripped = self._strip_json_markdown(content)

        try:
            return json.loads(stripped)
        except json.JSONDecodeError as first_error:
            logger.warning("Direct JSON parsing failed: %s", first_error)

        json_candidate = self._find_json_object(stripped)

        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError as second_error:
            logger.warning("JSON object parsing failed: %s", second_error)

        repaired = self._escape_control_chars_inside_strings(json_candidate)
        return json.loads(repaired)

    def _strip_json_markdown(self, content: str) -> str:
        stripped = content.strip()

        if stripped.startswith("```json"):
            stripped = stripped.removeprefix("```json").strip()
        elif stripped.startswith("```"):
            stripped = stripped.removeprefix("```").strip()

        if stripped.endswith("```"):
            stripped = stripped.removesuffix("```").strip()

        return stripped

    def _find_json_object(self, content: str) -> str:
        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("GigaChat response does not contain a JSON object")

        return content[start:end + 1]

    def _escape_control_chars_inside_strings(self, content: str) -> str:
        result = []
        in_string = False
        escaped = False

        for char in content:
            if escaped:
                result.append(char)
                escaped = False
                continue

            if char == "\\":
                result.append(char)
                escaped = True
                continue

            if char == '"':
                result.append(char)
                in_string = not in_string
                continue

            if in_string:
                if char == "\n":
                    result.append("\\n")
                    continue
                if char == "\r":
                    result.append("\\r")
                    continue
                if char == "\t":
                    result.append("\\t")
                    continue
                if ord(char) < 32:
                    continue

            result.append(char)

        return "".join(result)

    def _normalize_result(
        self,
        data: dict,
        existing_categories: list,
        email_json: dict = None,
    ) -> dict:
        logger.debug("Normalizing GigaChat result: data=%s", data)

        original_subject, original_body = self._original_text(email_json)

        is_new_category = self._as_bool(data.get("is_new_category"), False)
        category = str(data.get("category") or "unknown").strip()

        if is_new_category:
            category = self._normalize_new_category_name(
                category=category,
                title=data.get("new_category_title"),
            )

            if category in existing_categories:
                is_new_category = False
            elif category == "unknown":
                is_new_category = False
        elif category not in existing_categories:
            aliased_category = self._category_alias(category, existing_categories)
            if aliased_category:
                logger.info(
                    "GigaChat category alias applied: category=%s aliased_category=%s",
                    category,
                    aliased_category,
                )
                category = aliased_category
            else:
                logger.warning(
                    "GigaChat returned category not present in existing_categories: category=%s existing_categories=%s",
                    category,
                    existing_categories,
                )
                category = "unknown"

        try:
            confidence = float(data.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5

        confidence = max(0.0, min(1.0, confidence))

        grammar_corrections = self._normalize_grammar_corrections(
            data.get("grammar_corrections")
        )
        grammar_issues_found = self._as_bool(
            data.get("grammar_issues_found"),
            bool(grammar_corrections),
        )

        return {
            "category": category,
            "confidence": confidence,
            "method": "llm_gigachat",
            "reason": str(data.get("reason") or "GigaChat suggested category"),
            "is_new_category": is_new_category,
            "new_category_title": str(data.get("new_category_title") or category),
            "new_category_description": str(data.get("new_category_description") or ""),
            "corrected_subject": self._as_text(data.get("corrected_subject"), original_subject),
            "corrected_body": self._as_text(data.get("corrected_body"), original_body),
            "grammar_issues_found": grammar_issues_found,
            "grammar_corrections": grammar_corrections,
        }

    def _category_alias(self, category: str, existing_categories: list) -> Optional[str]:
        normalized = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ_]+", "_", category.lower()).strip("_")
        aliases = {
            "corporate_news": "newsletter",
            "company_news": "newsletter",
            "news": "newsletter",
            "digest": "newsletter",
            "дайджест": "newsletter",
            "новости": "newsletter",
            "equipment": "equipment_issue",
            "hardware": "equipment_issue",
            "printer_issue": "equipment_issue",
            "document": "document_review",
            "documents": "document_review",
            "document_approval": "document_review",
            "docs_review": "document_review",
            "finance": "financial_documents",
            "invoice": "financial_documents",
            "payment": "financial_documents",
            "access": "access_request",
            "permissions": "access_request",
            "technical": "technical_issue",
            "tech_issue": "technical_issue",
            "incident_report": "incident",
            "customer": "customer_question",
            "client_question": "customer_question",
            "phishing": "spam",
        }

        target = aliases.get(normalized)
        if target in existing_categories:
            return target

        return None

    def _fallback_result(self, reason: str, email_json: dict = None) -> dict:
        logger.warning("Using GigaChat fallback result: %s", reason)
        original_subject, original_body = self._original_text(email_json)

        return {
            "category": "unknown",
            "confidence": 0.0,
            "method": "llm_unavailable",
            "reason": reason,
            "is_new_category": False,
            "new_category_title": None,
            "new_category_description": None,
            "corrected_subject": original_subject,
            "corrected_body": original_body,
            "grammar_issues_found": False,
            "grammar_corrections": [],
        }

    def _original_text(self, email_json: dict = None) -> tuple[str, str]:
        email = (email_json or {}).get("email") or {}
        return email.get("subject") or "", email.get("body") or ""

    def _as_text(self, value, default: str) -> str:
        if value is None:
            return default

        return str(value)

    def _as_bool(self, value, default: bool) -> bool:
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "да"}:
                return True
            if normalized in {"false", "0", "no", "нет"}:
                return False

        return bool(value)

    def _normalize_new_category_name(self, category: str, title: str = None) -> str:
        source = category
        if not source or source == "unknown":
            source = title or "unknown"

        normalized = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ_]+", "_", str(source).strip().lower())
        normalized = re.sub(r"_+", "_", normalized).strip("_")

        return normalized or "unknown"

    def _normalize_grammar_corrections(self, value) -> list:
        if not isinstance(value, list):
            return []

        allowed_types = {"grammar", "spelling", "punctuation", "style"}
        corrections = []

        for item in value:
            if not isinstance(item, dict):
                continue

            correction_type = str(item.get("type") or "style")
            if correction_type not in allowed_types:
                correction_type = "style"

            corrections.append(
                {
                    "original": str(item.get("original") or ""),
                    "corrected": str(item.get("corrected") or ""),
                    "type": correction_type,
                    "explanation": str(item.get("explanation") or ""),
                }
            )

        return corrections
