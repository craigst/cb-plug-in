
from __future__ import annotations
import asyncio, signal
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Optional, Type

class FFmpegRecorder:
    def __init__(self, url: str, base_media: Path, name: str) -> None:
        self.url = url
        self.base_media = base_media
        self.name = name
        self.process: Optional[asyncio.subprocess.Process] = None
        self.current_file: Optional[Path] = None

    def _out_path(self) -> Path:
        now = datetime.now(timezone.utc)
        folder = self.base_media / self.name
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{self.name}_{now:%Y%m%d_%H%M%S}.mkv"

    async def start(self) -> Path:
        if self.process and self.process.returncode is None:
            if self.current_file is None:
                self.current_file = self._out_path()
            return self.current_file
        outfile = self._out_path()
        cmd = ["ffmpeg", "-nostdin", "-y", "-i", self.url, "-c", "copy", "-movflags", "+faststart", str(outfile)]
        self.current_file = outfile
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return outfile

    async def stop(self) -> None:
        if not self.process:
            return
        if self.process.returncode is None:
            try:
                self.process.send_signal(signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(self.process.wait(), timeout=10)
            except asyncio.TimeoutError:
                try:
                    self.process.kill()
                except ProcessLookupError:
                    pass
        self.process = None
        self.current_file = None

    async def __aenter__(self) -> FFmpegRecorder:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.stop()

    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    def pid(self) -> Optional[int]:
        return self.process.pid if self.is_running() else None

    async def convert_to_mp4(self, mkv_path: Path) -> Optional[Path]:
        mp4_path = mkv_path.with_suffix('.mp4')
        cmd = ["ffmpeg", "-i", str(mkv_path), "-c", "copy", "-movflags", "+faststart", str(mp4_path)]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(process.wait(), timeout=300)  # 5 min timeout
            if process.returncode == 0:
                return mp4_path
            else:
                return None
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            return None
