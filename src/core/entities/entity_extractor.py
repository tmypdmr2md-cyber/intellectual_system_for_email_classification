
"""EntityExtractor извлекает из письма важные сущности 
(системы, подразделения, вложения, коды ошибок) 
и преобразует неструктурированный текст в набор признаков.
 Эти данные используются для более точной классификации писем, 
 передачи дополнительного контекста в GigaChat и отображения объяснимой информации в интерфейсе системы."""
class EntityExtractor:
    def __init__(self):
        self.systems = [
            "vpn",
            "gitlab",
            "confluence",
            "active directory",
            "1c",
            "slack",
            "zoom",
            "excel",
            "adobe reader",
            "chrome",
            "outlook",
            "корпоративный портал",
            "облачное хранилище",
            "bi-система",
            "service desk",
        ]

        self.departments = [
            "hr",
            "it",
            "маркетинг",
            "продажи",
            "логистика",
            "закупки",
            "безопасность",
            "аналитика",
            "юристы",
        ]

    def extract(self, email_json: dict) -> dict:
        email = email_json.get("email") or {}

        subject = email.get("subject") or ""
        body = email.get("body") or ""
        error_code = email.get("error_code")
        attachments = email.get("attachments") or []

        text = f"{subject} {body}".lower()

        found_systems = []

        for system in self.systems:
            if system in text:
                found_systems.append(system)

        found_departments = []

        for department in self.departments:
            if department in text:
                found_departments.append(department)

        return {
            "systems": found_systems,
            "departments": found_departments,
            "error_code": error_code,
            "attachments": attachments,
            "has_attachments": len(attachments) > 0,
        }