from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class TempFileCleanup:
    """Background daemon that removes stale files from *upload_folder*.

    Files older than *max_age* seconds are deleted.  The sweep runs every
    *interval* seconds.  The thread is a daemon so it exits automatically
    when the main process does.
    """

    def __init__(self, upload_folder: str, max_age: int = 600, interval: int = 300):
        self.upload_folder = Path(upload_folder)
        self.max_age = max_age
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True, name="img-cleanup")
        self._thread.start()
        logger.info(
            "TempFileCleanup started (max_age=%ds, interval=%ds)", self.max_age, self.interval
        )

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------
    def _loop(self) -> None:
        while not self._stop.is_set():
            self.sweep()
            self._stop.wait(self.interval)

    def sweep(self) -> int:
        """Delete expired files.  Returns number of files removed."""
        if not self.upload_folder.is_dir():
            return 0

        now = time.time()
        removed = 0
        for path in self.upload_folder.iterdir():
            if not path.is_file():
                continue
            try:
                age = now - path.stat().st_mtime
                if age > self.max_age:
                    path.unlink()
                    removed += 1
            except OSError as exc:
                logger.warning("Could not remove %s: %s", path, exc)

        if removed:
            logger.info("Cleanup swept %d expired temp file(s).", removed)
        return removed
