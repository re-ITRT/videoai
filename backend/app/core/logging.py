"""结构化日志配置 — structlog + 文件输出 + JSON"""
import structlog
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "/app/logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def setup_logging():
    """配置 structlog + 文件 + stdout"""
    os.makedirs(LOG_DIR, exist_ok=True)

    # 文件日志（JSON 格式，持久化）
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    ))

    # 控制台日志（彩色可读）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    console_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
    ))

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def get_logger(name: str | None = None):
    return structlog.get_logger(name or __name__)
