from loguru import logger
from typing import Union

import sys


def setup_logger() -> None:
    logger.remove(0)
    logger.level("STATS", no=15)
    logger.add(sys.stderr, format="[{time}] | {level} | {message}", level="INFO")
    logger.add(sys.stderr, format="[{time}] | {level} | {message}", level="STATS")


def add_file_logger(
    path: str, rotation: str = "10MB", retention: Union[int, str] = 1
) -> None:
    logger.add(path, rotation=rotation, retention=retention)
