import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.routes.db import router as db_router
from src.api.routes.emails import router as emails_router
from src.api.routes.processing import router as processing_router
from src.core import config


BASE_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = Path(config.LOG_FILE)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        ),
    ],
    force=True,
)

logger = logging.getLogger(__name__)
logger.info("Logging initialized. Log file: %s", LOG_FILE)

app = FastAPI(
    title="Email Classification System",
    version="0.1.0",
)

logger.info("FastAPI application initialized")


app.include_router(emails_router)
app.include_router(processing_router)
app.include_router(db_router)

admin_panel_dir = Path(__file__).resolve().parents[1] / "admin_panel"
app.mount(
    "/dashboard",
    StaticFiles(directory=admin_panel_dir, html=True),
    name="dashboard",
)


@app.get("/")
def read_root():
    return {
        "Status": "fastapi is working"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }
