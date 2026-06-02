# Email Classification System

## Быстрый запуск

Команды выполнять из корня проекта, где находится папка `src`.

### 1. Установить окружение

```bash
src/bash/setup_env.sh
```

Проект рассчитан на Python 3.9.6.

### 2. Поднять PostgreSQL

```bash
src/bash/start_db.sh
```

### 3. Создать таблицы (инициализация db)

```bash
src/bash/init_db.sh
```

### 4. Запустить приложение

```bash
src/bash/run_api.sh
```

После запуска:

```text
API:        http://127.0.0.1:8000
Тут готовая панель от FastAPI со всемии эндпоинтами:    http://127.0.0.1:8000/docs
Наша админ UI для вашего удобства, чтобы можно 
было красиво просмотреть и все протестировать и потыкать:   http://127.0.0.1:8000/dashboard/
```

## Admin панель

Открыть:

```text
http://127.0.0.1:8000/dashboard/
```

Что можно сделать в панели:

- посмотреть статистику по БД;
- увидеть все файлы из inbox;
- загрузить письма в БД;
- обработать следующие 5 писем;
- обработать все письма;
- очистить и переинициализировать БД;
- посмотреть письма, категории, confidence, method, reason, entities и похожие письма.

## Основной сценарий

Через UI:

1. Открыть `/dashboard/`.
2. Нажать `Очистить БД`, если нужен чистый прогон.
3. Нажать `Загрузить inbox`.
4. Нажать `Process next 5` или `Process all`.
5. Смотреть результаты в таблицах и наслаждаться.

Через терминал:

```bash
src/bash/reset_db.sh
src/bash/ingest.sh
src/bash/process_next.sh
src/bash/health.sh
```

Для обработки всех писем:

```bash
src/bash/process_all.sh
```

Для демо-пайплайна:

```bash
src/bash/pipeline_demo.sh
```

## Тесты

Запуск:

```bash
src/bash/run_tests.sh
```

Тесты лежат в `src/tests` и проверяют:

- парсер писем;
- rule-based классификатор;
- decision engine;
- entity extraction;
- semantic search;
- GigaChat клиент без реального сетевого запроса;
- регистрацию основных FastAPI routes.

## База данных

PostgreSQL поднимается через:

```bash
src/docker-compose.yml
```

Сброс и переинициализация БД:

```bash
src/bash/reset_db.sh
```

Или через API:

```http
POST /db/reset
```

## Важные endpoints

```http
GET  /health
POST /emails/ingest
GET  /emails/list
GET  /emails/{email_id}
POST /processing/process-next?limit=5
POST /processing/process-all
GET  /db/overview
POST /db/reset
GET  /db/inbox-files
GET  /categories/list
GET  /categories/{category_id}/emails
GET  /classification-results/list
```

## Архитектура

```text
src/
  app/                 FastAPI app
  api/routes/          HTTP endpoints для каждого сервиса
  services/            ingestion и processing pipeline для запуска парсинга и сохранения и основной пайплайн классификации
  core/parser/         парсинг файлов писем
  core/classification/ базовый rule based классификатор
  core/embeddings/     sentence transformers embeddings
  core/semantic_search поиск похожих писем
  core/entities/       извлечение сущностей
  core/decision/       финальное решение
  core/llm/            GigaChat fallback
  db/                  SQLAlchemy models/repositories/session
  admin_panel/         HTML/CSS/JS dashboard
  tests/               unittest tests
  bash/                скрипты запуска
```

## GigaChat

Конфиг загружается из двух мест:

- `.env` в корне проекта;
- `src/.env`.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/email_classifier

# НЕ МЕНЯТЬ, РАССЧИТАНО ПРОФЕССИОНАЛАМИ НА ОСНОВЕ ЭКСПЕРИМЕНТОВ И ДОЛГОЙ РУЧНОЙ АНАЛИТИКИ
RULE_CONFIDENCE_THRESHOLD=0.80
# НЕ МЕНЯТЬ, РАССЧИТАНО ПРОФЕССИОНАЛАМИ НА ОСНОВЕ ЭКСПЕРИМЕНТОВ И ДОЛГОЙ РУЧНОЙ АНАЛИТИКИ
SEMANTIC_SIMILARITY_THRESHOLD=0.75
PROCESSING_CONCURRENCY=5

EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

GIGA_CHAT_API_KEY=your_base64_authorization_key
GIGA_CHAT_SCOPE=GIGACHAT_API_PERS
GIGA_CHAT_MODEL=GigaChat-2
GIGA_CHAT_VERIFY_SSL=false
GIGA_CHAT_TIMEOUT=30

LOG_LEVEL=INFO
LOG_FILE=logs/app.log

```

GigaChat вызывается только если rule-based классификатор и semantic search не дали уверенного решения. Если API недоступен или ключ не был загружен, система возвращает `llm_unavailable`, а итоговая категория чаще всего остается `unknown`.

## Embeddings

Semantic search использует:

```env
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Модель грузится с `local_files_only=True`, поэтому она должна быть заранее скачана в кеш HuggingFace текущего пользователя.
Если модели нет, обработка писем может падать в `failed` на этапе embeddings.

## Почему письма уходят в unknown

Основной pipeline:

1. Rule-based classifier
2. Semantic search по уже классифицированным письмам
3. GigaChat fallback

Для аудита конкретного запуска смотрите `logs/app.log`: там видно, какой слой принял решение (`rule_based`, `semantic_search`, `llm_gigachat`, `llm_unavailable`) и почему.

## Заметки

- Rule-based классификатор специально оставлен базовым, чтобы semantic search и LLM fallback реально участвовали в pipeline.
то есть сначала мы сделали подробные правила, но так как в нашей идеи было сделать дополнительные инстурменты для расширенного поиска с возможностью будущего масштабирования, то правила специально были облегчены, будто бы мы не видели что было внутри нашего
inbox
- Новые категории создаются только из финального решения `DecisionEngine`; GigaChat ограничен списком разрешенных категорий.

## Проверка скачанных моделей HuggingFace чтобы понимать ставить True на локал модели или нет (я закомментировал этот момент)

```bash
ls ~/.cache/huggingface/hub
```

Example: models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2
модель которую мы использовали
