import logging
import sys

def setup_logger(name: str = "XAI_Reviewer") -> logging.Logger:
    """Configure structured logging with console + file output."""
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)

    # Prevent duplicate handlers on re-import
    if log.handlers:
        return log

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    log.addHandler(console)

    # File handler — captures everything for debugging
    try:
        file_handler = logging.FileHandler("xai_reviewer.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)
    except OSError:
        log.warning("Could not create log file. Logging to console only.")

    return log

logger = setup_logger()