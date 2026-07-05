import logging
import json
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Inject traceback details if an exception is handled
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        # Capture any extra contextual dictionaries passed into the log statement
        if hasattr(record, "extra_context"):
            log_object["context"] = record.extra_context

        return json.dumps(log_object)


def setup_logging():
    logger = logging.getLogger("resume_screener")
    logger.setLevel(logging.INFO)

    # Direct logs cleanly to stdout for cloud logging router consumption
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Avoid duplicate logs if configured multiple times
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# Single globally exported logger instance
logger = setup_logging()
