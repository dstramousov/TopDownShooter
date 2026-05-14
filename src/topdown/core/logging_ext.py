from __future__ import annotations

import json
import logging
from logging import Logger
from pathlib import Path
from pprint import pformat
from typing import Any

from topdown.core.config import LoggingConfig

_COLOR_MAP = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[35m",
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    """Console formatter with ANSI colors."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = _COLOR_MAP.get(record.levelno, "")
        if not color:
            return message
        return f"{color}{message}{_RESET}"


class ProjectLoggerAdapter(logging.LoggerAdapter):
    """Small helper wrapper around the standard logger."""

    def dump_object(self, title: str, payload: Any) -> None:
        """Log a formatted representation of an object.

        Args:
            title: Context title.
            payload: Any serializable or repr-friendly object.
        """
        try:
            serialized = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
        except TypeError:
            serialized = pformat(payload, width=100)
        self.logger.debug("%s\n%s", title, serialized)

    def exception_with_context(self, message: str, **context: Any) -> None:
        """Log exception details together with structured context.

        Args:
            message: Human-readable message.
            **context: Additional diagnostic fields.
        """
        if context:
            self.logger.exception("%s | context=%s", message, pformat(context, width=100))
            return
        self.logger.exception(message)


def configure_logging(config: LoggingConfig, project_root: Path) -> ProjectLoggerAdapter:
    """Configure application logging.

    Args:
        config: Logging configuration.
        project_root: Project root used to resolve the log file path.

    Returns:
        Configured project logger adapter.
    """
    logger = logging.getLogger("topdown")
    logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter_class = _ColorFormatter if config.use_colors else logging.Formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        formatter_class("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    logger.addHandler(console_handler)

    if config.log_to_file:
        log_path = project_root / config.file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        logger.addHandler(file_handler)

    return ProjectLoggerAdapter(logger, extra={})
