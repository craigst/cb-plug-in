"""File manager for handling local recording and NAS transfers."""
from __future__ import annotations
import asyncio
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "chaturbate_bridge.file_manager"


class FileManager:
    """Manages recording files and transfers between local and remote storage."""

    def __init__(
        self,
        hass: HomeAssistant,
        local_path: str,
        remote_path: str,
        enable_auto_move: bool = True,
        nas_check_interval: int = 60,
        auto_cleanup: bool = False,
        retention_days: int = 30,
        min_free_space_gb: float = 10,
    ) -> None:
        """Initialize the file manager."""
        self.hass = hass
        self._local_path = Path(local_path)
        self._remote_path = Path(remote_path) if remote_path and remote_path.strip() else None
        self._enable_auto_move = enable_auto_move and self._remote_path is not None
        self._nas_check_interval = nas_check_interval
        self._auto_cleanup = auto_cleanup
        self._retention_days = retention_days
        self._min_free_space_gb = min_free_space_gb
        
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._pending_moves: List[Dict[str, Any]] = []
        self._nas_online = False
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self._stats = {
            "total_moved": 0,
            "total_moved_bytes": 0,
            "failed_moves": 0,
            "last_move_time": None,
            "nas_status": "unknown",
            "pending_files": 0,
        }

    async def async_start(self) -> None:
        """Start the file manager."""
        # Load pending moves from storage
        data = await self._store.async_load() or {}
        self._pending_moves = data.get("pending_moves", [])
        self._stats.update(data.get("stats", {}))
        
        # Ensure local directory exists
        await self.hass.async_add_executor_job(
            lambda: self._local_path.mkdir(parents=True, exist_ok=True)
        )
        
        # Start the background task
        self._running = True
        self._task = asyncio.create_task(self._run())
        _LOGGER.info(
            "File manager started: local=%s, remote=%s, auto_move=%s",
            self._local_path,
            self._remote_path,
            self._enable_auto_move,
        )

    async def async_stop(self) -> None:
        """Stop the file manager."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._save_state()
        _LOGGER.info("File manager stopped")

    def get_local_path(self, model: str) -> Path:
        """Get the local recording path for a model."""
        path = self._local_path / model
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_remote_path(self, model: str) -> Optional[Path]:
        """Get the remote recording path for a model."""
        if not self._remote_path:
            return None
        path = self._remote_path / model
        return path

    async def queue_file_move(self, file_path: Path, model: str) -> None:
        """Queue a file for moving to remote storage."""
        if not self._enable_auto_move or not self._remote_path:
            return
        
        move_info = {
            "source": str(file_path),
            "model": model,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "attempts": 0,
        }
        self._pending_moves.append(move_info)
        self._stats["pending_files"] = len(self._pending_moves)
        await self._save_state()
        _LOGGER.debug("Queued file for move: %s", file_path)

    def _check_nas_available(self) -> bool:
        """Check if NAS/remote storage is available."""
        if not self._remote_path:
            return False
        
        try:
            # Check if path exists and is writable
            if not self._remote_path.exists():
                return False
            
            # Try to create a test file
            test_file = self._remote_path / ".chaturbate_bridge_test"
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError) as exc:
            _LOGGER.debug("NAS check failed: %s", exc)
            return False

    async def _move_file(self, move_info: Dict[str, Any]) -> bool:
        """Move a file from local to remote storage."""
        source = Path(move_info["source"])
        model = move_info["model"]
        
        if not source.exists():
            _LOGGER.warning("Source file no longer exists: %s", source)
            return True  # Remove from queue
        
        try:
            # Ensure remote directory exists
            remote_dir = self._remote_path / model
            remote_dir.mkdir(parents=True, exist_ok=True)
            
            # Destination path
            dest = remote_dir / source.name
            
            # Move file
            await self.hass.async_add_executor_job(shutil.move, str(source), str(dest))
            
            # Update statistics
            self._stats["total_moved"] += 1
            try:
                self._stats["total_moved_bytes"] += dest.stat().st_size
            except OSError:
                pass
            self._stats["last_move_time"] = datetime.now(timezone.utc).isoformat()
            
            _LOGGER.info("Moved recording to NAS: %s -> %s", source, dest)
            return True
        except Exception as exc:
            _LOGGER.error("Failed to move file %s: %s", source, exc)
            move_info["attempts"] += 1
            self._stats["failed_moves"] += 1
            
            # Remove from queue after 5 failed attempts
            if move_info["attempts"] >= 5:
                _LOGGER.error("Giving up on moving file after 5 attempts: %s", source)
                return True
            
            return False

    async def _process_pending_moves(self) -> None:
        """Process pending file moves."""
        if not self._pending_moves or not self._nas_online:
            return
        
        completed = []
        for i, move_info in enumerate(self._pending_moves):
            if await self._move_file(move_info):
                completed.append(i)
        
        # Remove completed moves
        for i in reversed(completed):
            self._pending_moves.pop(i)
        
        self._stats["pending_files"] = len(self._pending_moves)
        
        if completed:
            await self._save_state()

    async def _cleanup_old_files(self) -> None:
        """Clean up old recordings based on retention policy."""
        if not self._auto_cleanup or self._retention_days <= 0:
            return
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        
        # Cleanup local files
        await self._cleanup_directory(self._local_path, cutoff)
        
        # Cleanup remote files if enabled
        if self._remote_path and self._nas_online:
            await self._cleanup_directory(self._remote_path, cutoff)

    async def _cleanup_directory(self, directory: Path, cutoff: datetime) -> None:
        """Clean up old files in a directory."""
        if not directory.exists():
            return
        
        try:
            for file_path in directory.rglob("*.mkv"):
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        await self.hass.async_add_executor_job(file_path.unlink)
                        _LOGGER.info("Deleted old recording: %s", file_path)
                except OSError as exc:
                    _LOGGER.debug("Failed to delete file %s: %s", file_path, exc)
        except Exception as exc:
            _LOGGER.error("Error during cleanup of %s: %s", directory, exc)

    async def _check_disk_space(self) -> None:
        """Check if local disk has enough free space."""
        try:
            stat = await self.hass.async_add_executor_job(shutil.disk_usage, str(self._local_path))
            free_gb = stat.free / (1024 ** 3)
            
            if free_gb < self._min_free_space_gb:
                _LOGGER.warning(
                    "Low disk space on local storage: %.2f GB free (minimum: %.2f GB)",
                    free_gb,
                    self._min_free_space_gb,
                )
        except Exception as exc:
            _LOGGER.debug("Failed to check disk space: %s", exc)

    async def _run(self) -> None:
        """Main background task loop."""
        cleanup_counter = 0
        
        while self._running:
            try:
                # Check NAS availability
                old_status = self._nas_online
                self._nas_online = await self.hass.async_add_executor_job(self._check_nas_available)
                
                if self._nas_online != old_status:
                    status = "online" if self._nas_online else "offline"
                    self._stats["nas_status"] = status
                    _LOGGER.info("NAS status changed: %s", status)
                
                # Process pending moves if NAS is online
                if self._nas_online and self._pending_moves:
                    await self._process_pending_moves()
                
                # Check disk space
                await self._check_disk_space()
                
                # Cleanup old files (once per hour)
                cleanup_counter += 1
                if cleanup_counter >= 60:  # Every 60 cycles (60 minutes if interval is 60s)
                    await self._cleanup_old_files()
                    cleanup_counter = 0
                
                # Wait for next check
                await asyncio.sleep(self._nas_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _LOGGER.error("Error in file manager loop: %s", exc)
                await asyncio.sleep(self._nas_check_interval)

    async def _save_state(self) -> None:
        """Save state to storage."""
        try:
            data = {
                "pending_moves": self._pending_moves,
                "stats": self._stats,
            }
            await self._store.async_save(data)
        except Exception as exc:
            _LOGGER.error("Failed to save file manager state: %s", exc)

    def get_stats(self) -> Dict[str, Any]:
        """Get file manager statistics."""
        return {
            **self._stats,
            "nas_online": self._nas_online,
            "local_path": str(self._local_path),
            "remote_path": str(self._remote_path) if self._remote_path else None,
            "auto_move_enabled": self._enable_auto_move,
        }

    def is_nas_online(self) -> bool:
        """Check if NAS is currently online."""
        return self._nas_online
