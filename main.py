from __future__ import annotations

import sys

from utils.logging_config import configure_logging, get_logger
from utils.settings import load_settings


def main() -> int:
    settings = load_settings()
    configure_logging(settings.paths.logs_dir)
    logger = get_logger(__name__)
    logger.info("Starting Music Lyriz")

    try:
        from ui.app import run_app
    except ImportError as exc:
        logger.exception("Unable to import the Qt application")
        print(
            "Music Lyriz needs PySide6 to run the desktop UI. "
            "Install dependencies with: pip install -r requirements.txt",
            file=sys.stderr,
        )
        print(f"Import error: {exc}", file=sys.stderr)
        return 1

    return run_app(settings)


if __name__ == "__main__":
    raise SystemExit(main())
