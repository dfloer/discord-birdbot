from .logging_config import setup_logger, add_file_logger
import os

setup_logger()

# There was no reasonable way to accomplish this. It's an awful hack, but otherwise, there's no way to properly disable file logging for pytest.
# Why not run logger.disable("") in pytest? This just disables writing to the log file, it doesn't disable file logging, which causes blank log files, which is bad.
# Monkeypatching also didn't work, because you can't monkeypatch an __init__.py before you've loaded it.
# So this was the only way to check if this is being run through pytest. Yep...
if not any([True for x, y in os.environ.items() if "pytest" in x.lower() or "pytest" in y.lower()]):
    add_file_logger("logs/lookupcog-{time}.log")
