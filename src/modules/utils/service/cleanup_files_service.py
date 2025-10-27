import asyncio
import logging
import time
from pathlib import Path

from attrs import define, field


@define
class CleanupService:
    """
    A background service that periodically cleans up old music files.
    """

    target_dir: Path = Path("downloads/")
    max_age_hours: int = 10
    interval_seconds: int = 3600
    max_total_size_mb: int = 400
    logger: logging.Logger = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def run(self) -> None:
        """Run cleanup periodically in the background."""
        self.logger.info(
            f"CleanupService started — every {self.interval_seconds // 60} min, "
            f"max age {self.max_age_hours}h, max size {self.max_total_size_mb}MB."
        )

        while True:
            try:
                await self._cleanup_old_files()
                await self._enforce_size_limit()
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
            await asyncio.sleep(self.interval_seconds)

    async def _cleanup_old_files(self) -> None:
        if not self.target_dir.exists():
            return

        now = time.time()
        threshold = now - (self.max_age_hours * 3600)
        deleted_files = []

        for file in self.target_dir.iterdir():
            if file.is_file() and file.stat().st_mtime < threshold:
                try:
                    file.unlink()
                    deleted_files.append(file.name)
                except Exception as e:
                    self.logger.warning(f"Could not delete {file.name}: {e}")

        if deleted_files:
            files_list = ", ".join(deleted_files)
            self.logger.info(f"Deleted {len(deleted_files)} old files: {files_list}")

    async def _enforce_size_limit(self) -> None:
        if not self.target_dir.exists():
            return

        files = [f for f in self.target_dir.iterdir() if f.is_file()]
        files.sort(key=lambda f: f.stat().st_mtime)

        total_size = sum(f.stat().st_size for f in files) / (1024 * 1024)
        deleted = 0

        while total_size > self.max_total_size_mb and files:
            oldest = files.pop(0)
            try:
                size_mb = oldest.stat().st_size / (1024 * 1024)
                oldest.unlink()
                total_size -= size_mb
                deleted += 1
            except Exception as e:
                self.logger.warning(f"Could not delete {oldest}: {e}")

        if deleted:
            self.logger.info(
                f"Enforced size limit — deleted {deleted} files, "
                f"current total: {total_size:.2f} MB"
            )
