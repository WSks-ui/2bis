import logging


LOG_FORMAT = "%(asctime)s.%(msecs)03d [%(name)s] %(levelname)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=DATE_FORMAT, force=True)
    for logger_name in (
        "ai_client",
        "generation_worker",
        "httpx",
        "task_queue",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    ):
        logging.getLogger(logger_name).setLevel(level)
