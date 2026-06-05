import logging

from sdlc.utils.logging import get_logger, log_event


def test_get_logger_returns_logger():
    logger = get_logger("test_sdlc_logger_1")
    assert isinstance(logger, logging.Logger)


def test_get_logger_same_name_returns_same():
    l1 = get_logger("test_sdlc_logger_2")
    l2 = get_logger("test_sdlc_logger_2")
    assert l1 is l2


def test_log_event_no_exception():
    log_event("test_event", key1="val1", key2="val2")
