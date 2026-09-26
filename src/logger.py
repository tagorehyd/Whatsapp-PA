import logging
import os


def create_logger() -> logging.Logger:
    logger = logging.getLogger("wa_llm_bot")
    logger.setLevel(logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


logger = create_logger()
