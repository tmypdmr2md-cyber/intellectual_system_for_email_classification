import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
ENV_FILE = PROJECT_ROOT / ".env"
SRC_ENV_FILE = SRC_DIR / ".env"

load_dotenv(ENV_FILE)
load_dotenv(SRC_ENV_FILE)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


RULE_CONFIDENCE_THRESHOLD = _float_env("RULE_CONFIDENCE_THRESHOLD", 0.85)
SEMANTIC_SIMILARITY_THRESHOLD = _float_env("SEMANTIC_SIMILARITY_THRESHOLD", 0.75)

PROCESSING_CONCURRENCY = _int_env("PROCESSING_CONCURRENCY", 5)

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

GIGACHAT_CREDENTIALS = (
    os.getenv("GIGA_CHAT_API_KEY")
    or os.getenv("GIGACHAT_CREDENTIALS")
    or ""
).strip()
GIGACHAT_SCOPE = os.getenv("GIGA_CHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_MODEL = os.getenv("GIGA_CHAT_MODEL", "GigaChat-2")
GIGACHAT_AUTH_URL = os.getenv(
    "GIGA_CHAT_AUTH_URL",
    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
)
GIGACHAT_CHAT_URL = os.getenv(
    "GIGA_CHAT_CHAT_URL",
    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
)
GIGACHAT_TIMEOUT = _float_env("GIGA_CHAT_TIMEOUT", 30.0)
GIGACHAT_VERIFY_SSL = os.getenv("GIGA_CHAT_VERIFY_SSL", "false").lower() == "true"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(PROJECT_ROOT / "logs" / "app.log"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/email_classifier",
)

DEFAULT_CATEGORIES = [
    {
        "name": "urgent",
        "title": "Срочное",
        "description": "Срочные письма, критичные обращения, высокий приоритет, блокировка работы",
    },
    {
        "name": "incident",
        "title": "Инциденты",
        "description": "Массовые сбои, критические ошибки, недоступность сервисов, остановка работы",
    },
    {
        "name": "monitoring_alert",
        "title": "Мониторинг",
        "description": (
            "Автоматические уведомления мониторинга, Grafana, WARNING/CRITICAL/INFO, "
            "метрики CPU/Disk/Uptime, структурированные блоки Сервис/Статус/Метрика/Время"
        ),
    },
    {
        "name": "access_request",
        "title": "Запросы доступа",
        "description": (
            "VPN, GitLab, Confluence, Active Directory, 1C, корпоративная почта, "
            "облачное хранилище, система согласования, права, роли"
        ),
    },
    {
        "name": "technical_issue",
        "title": "Технические проблемы",
        "description": "Ошибки, неработающие приложения, проблемы с API, Outlook, антивирусом, порталами, сервисами",
    },
    {
        "name": "equipment_issue",
        "title": "Оборудование",
        "description": "Принтеры, сканеры, ноутбуки, мыши, гарнитуры, мониторы, ремонт, диагностика, замена",
    },
    {
        "name": "financial_documents",
        "title": "Финансовые документы",
        "description": "Счета, акты, договоры, закрывающие документы, оплата, invoice, contract",
    },
    {
        "name": "document_review",
        "title": "Документы на согласование",
        "description": "Правки, версии документов, инструкции, технические задания, комментарии",
    },
    {
        "name": "hr_request",
        "title": "HR-запросы",
        "description": "Отпуск, больничный, новый сотрудник, рабочее место, график работы",
    },
    {
        "name": "meeting",
        "title": "Встречи и созвоны",
        "description": "Демо, встречи, созвоны, обсуждение статуса задач",
    },
    {
        "name": "newsletter",
        "title": "Дайджесты и новости",
        "description": "Корпоративные новости, дайджесты, обновления портала, итоги квартала",
    },
    {
        "name": "spam",
        "title": "Спам и фишинг",
        "description": "Розыгрыши, подозрительные ссылки, запросы логина/пароля, банковские карты, блокировка аккаунта",
    },
    {
        "name": "customer_question",
        "title": "Вопросы клиентов",
        "description": "Вопросы партнёров и клиентов, жалобы, запросы инструкций",
    },
    {
        "name": "garbage",
        "title": "Мусорные файлы",
        "description": "Битые JSON, бинарные файлы, пустые файлы, неподдерживаемые форматы",
    },
    {
        "name": "unknown",
        "title": "Неизвестно",
        "description": "Письма, которые не удалось уверенно классифицировать",
    },
]
