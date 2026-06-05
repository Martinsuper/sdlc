import logging
from typing import Any


def get_logger(name: str = "sdlc") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            fmt="[%(asctime)s] %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_event(event: str, **kwargs: Any) -> None:
    logger = get_logger()
    parts = " ".join(f"{k}={v}" for k, v in kwargs.items())
    msg = f"{event} | {parts}" if parts else event
    logger.info(msg)
