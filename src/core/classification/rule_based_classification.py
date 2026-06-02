class RuleBasedClassifier:
    def __init__(self):
        self.rules = {
            "urgent": [
                "срочно",
                "срочное",
                "urgent",
                "critical",
                "критично",
                "критический",
                "работа остановлена",
                "полностью остановлена",
                "массовый сбой",
                "недоступен",
                "инцидент",
                "блокирует работу",
            ],
            "monitoring_alert": [
                "мониторинг",
                "grafana",
                "[warning]",
                "[critical]",
                "[info]",
                "warning",
                "critical",
                "uptime:",
                "сервис:",
                "статус:",
                "метрика:",
                "время:",
                "cpu usage",
                "disk usage",
                "healthcheck",
                "автоматическое уведомление",
                "сгенерировано автоматически",
            ],
            "spam": [
                "вы выиграли",
                "розыгрыш",
                "exclusive offer",
                "limited time",
                "банковской карты",
                "подтвердите личность",
                "логин и пароль",
                "аккаунт будет заблокирован",
            ],
            "incident": [
                "инцидент",
                "массовый сбой",
                "работа остановлена",
                "остановка работы",
                "недоступен",
                "недоступность",
                "ошибка 500",
                "5xx",
            ],
            "access_request": [
                "доступ",
                "права",
                "запрос доступа",
                "нет доступа",
                "выдать права",
                "не могу войти",
                "vpn",
                "gitlab",
                "confluence",
                "active directory",
                "1c",
                "1с",
                "корпоративная почта",
                "облачное хранилище",
                "система согласования",
                "роль",
            ],
            "technical_issue": [
                "ошибка",
                "не работает",
                "не запускается",
                "зависает",
                "сломался",
                "не открывается",
                "неисправность",
                "проблема",
                "код ошибки",
            ],
            "equipment_issue": [
                "принтер",
                "сканер",
                "ноутбук",
                "мышь",
                "гарнитура",
                "монитор",
                "ремонт",
                "диагностика",
                "замена",
            ],
            "financial_documents": [
                "счёт",
                "счет",
                "оплата",
                "акт",
                "закрывающие документы",
                "договор",
                "invoice",
            ],
            "document_review": [
                "согласование",
                "правки",
                "версия документа",
                "инструкция",
                "техническое задание",
                "комментарии",
            ],
            "hr_request": [
                "отпуск",
                "больничный",
                "новый сотрудник",
                "рабочее место",
                "график работы",
            ],
            "meeting": [
                "созвон",
                "встреча",
                "демо",
                "приглашение",
                "обсудить",
            ],
            "newsletter": [
                "дайджест",
                "корпоративные новости",
                "новости",
                "обновления портала",
                "итоги квартала",
                "анонс",
            ],
            "customer_question": [
                "клиент",
                "партнёр",
                "партнер",
                "жалоба",
                "инструкция",
                "вопрос",
                "подскажите",
            ],
        }

        self.priority_categories = [
            "spam",
            "monitoring_alert",
            "urgent",
            "incident",
            "access_request",
            "technical_issue",
            "equipment_issue",
            "financial_documents",
            "document_review",
            "hr_request",
            "meeting",
            "newsletter",
            "customer_question",
        ]

    def classify(self, email_json: dict) -> dict:
        if email_json.get("is_garbage"):
            return {
                "category": "garbage",
                "confidence": 1.0,
                "method": "rule_based",
                "reason": f"Parser marked file as garbage: {email_json.get('status')}", 
            }

        email = email_json.get("email") or {}

        subject = email.get("subject") or ""
        body = email.get("body") or ""
        text = f"{subject} {body}".lower()

        is_monitoring_alert = self._is_monitoring_alert(text)
        has_business_critical_problem = self._has_business_critical_problem(text)

        if is_monitoring_alert and not has_business_critical_problem:
            return {
                "category": "monitoring_alert",
                "confidence": 0.9,
                "method": "rule_based",
                "reason": "Detected automatic monitoring alert",
            }

        scores = {}

        for category, keywords in self.rules.items():
            matched = [
                keyword
                for keyword in keywords
                if keyword.lower() in text
            ]

            if matched:
                scores[category] = matched

        if is_monitoring_alert and has_business_critical_problem:
            scores.pop("monitoring_alert", None)

        if not scores:
            return {
                "category": "unknown",
                "confidence": 0.0,
                "method": "rule_based",
                "reason": "No rule matched",
            }

        best_category = self._choose_best_category(scores)
        matched_keywords = scores[best_category]

        return {
            "category": best_category,
            "confidence": self._calculate_confidence(matched_keywords, scores),
            "method": "rule_based",
            "reason": f"Matched basic keywords: {', '.join(matched_keywords)}",
        }

    def _is_monitoring_alert(self, text: str) -> bool:
        structured_fields = [
            "сервис:",
            "статус:",
            "метрика:",
            "время:",
        ]
        structured_score = sum(1 for field in structured_fields if field in text)

        monitoring_markers = [
            "мониторинг",
            "grafana",
            "автоматическое уведомление",
            "сгенерировано автоматически",
            "uptime:",
            "disk usage",
            "cpu usage",
            "healthcheck",
            "[warning]",
            "[critical]",
            "[info]",
        ]

        return structured_score >= 3 or any(marker in text for marker in monitoring_markers)

    def _has_business_critical_problem(self, text: str) -> bool:
        business_markers = [
            "работа остановлена",
            "полностью остановлена",
            "блокирует работу",
            "массовый сбой",
            "пользователи не могут",
            "клиенты не могут",
            "остановка продаж",
            "остановка отгрузок",
        ]

        return any(marker in text for marker in business_markers)

    def _choose_best_category(self, scores: dict) -> str:
        best_category = None
        best_score = -1
        best_priority = len(self.priority_categories)

        for category, matched_keywords in scores.items():
            score = len(matched_keywords)
            if category in self.priority_categories:
                priority = self.priority_categories.index(category)
            else:
                priority = len(self.priority_categories)

            if score > best_score or (score == best_score and priority < best_priority):
                best_category = category
                best_score = score
                best_priority = priority

        return best_category

    def _calculate_confidence(self, matched_keywords: list, scores: dict) -> float:
        confidence = 0.35 + len(matched_keywords) * 0.12

        if len(scores) > 1:
            confidence -= 0.08

        if "urgent" in scores:
            confidence += 0.15

        if "spam" in scores and len(matched_keywords) >= 2:
            confidence += 0.1

        return round(max(0.0, min(0.95, confidence)), 2)
