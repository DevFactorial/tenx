import logging
import sys
import structlog
from app.core.config import settings

def setup_logging():
    # 1. Shared processors for both standard and structured logs
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]

    # 2. Production vs Development formatting
    if settings.ENVIRONMENT == "production":
        # JSON logs for ELK/Datadog
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty-print for local terminal
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 3. Intercept standard logging (from libraries like SQLAlchemy/Uvicorn)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )