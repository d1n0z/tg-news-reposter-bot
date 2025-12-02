import logging
import sys

from aiogram.dispatcher.event.bases import CancelHandler
from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


class SuppressCancelHandler(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info:
            exc_type, *_ = record.exc_info
            if exc_type is CancelHandler:
                return False
        return True


def setup_logger(
    logfile: str | None = "./logs/bot.log",
    filter_logfile: str | None = "./logs/filter.log",
    level: str = "INFO",
):
    logger.remove()

    logger.add(
        sys.stdout,
        level=level.upper(),
    )
    logger.debug("Added stdout handler with level: {}", level.upper())

    if logfile:
        logger.add(
            logfile,
            rotation="500MB",
            retention="2 weeks",
            compression="gz",
            enqueue=True,
            level="DEBUG",
        )
        logger.debug("Added file handler: {}", logfile)
    if filter_logfile:
        logger.add(
            filter_logfile,
            rotation="500MB",
            retention="4 weeks",
            compression="gz",
            enqueue=True,
            level="TRACE",
            format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
            filter=lambda record: record["extra"].get("filter_logger", False),
        )
        logger.debug("Added file handler: {}", logfile)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    logging.getLogger().handlers = [InterceptHandler()]
    logging.getLogger().setLevel(logging.DEBUG)

    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiogram.event").addFilter(SuppressCancelHandler())

    logger.debug("Logger successfully initialized")
