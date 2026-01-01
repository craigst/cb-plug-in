
from __future__ import annotations
import logging
from typing import Any, Dict, List
from pathlib import Path
from urllib.parse import urlparse, quote
from datetime import timedelta, datetime, timezone

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_AUTO_CONVERT_MP4,
    DEFAULT_GO2RTC_URL,
    DEFAULT_PUBLIC_GO2RTC_BASE,
    DEFAULT_RECORD_BASE,
    DOMAIN,
)
from .recorder import FFmpegRecorder

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.switch_states"

ATTR_RECORDING = "recording"
ATTR_FILEPATH = "file_path"
ATTR_PID = "pid"

SCAN_INTERVAL = timedelta(seconds=60)


def _resolve_base_folder(hass: HomeAssistant, record_base: str) -> Path:
    rb = (record_base or "").strip()
    if not rb:
        return Path("/media/chaturbate")
    if rb.startswith("/"):
        return Path(rb)
    if rb == "media" or rb == "/media":
        return Path("/media")
    if rb.startswith("media/"):
        return Path("/media") / rb.split("/", 1)[1]
    return Path(hass.config.path(rb))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    models: List[str] = data.get("models", [])
    file_manager = data.get("file_manager")
    base_source = data.get("public_go2rtc_base") or data.get("go2rtc_url") or DEFAULT_PUBLIC_GO2RTC_BASE or DEFAULT_GO2RTC_URL
    public_base: str = base_source.rstrip("/")

    parsed = urlparse(public_base)
    host = parsed.hostname or "127.0.0.1"
    rtsp_base = f"rtsp://{host}:8554"

    # Create shared storage for all switches
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored_data = await store.async_load() or {}

    entities: List[ChaturbateRecordSwitch] = []
    for m in models:
        url = f"{rtsp_base}/{quote(m, safe='')}"
        entities.append(ChaturbateRecordSwitch(hass, entry.entry_id, m, url, file_manager, store, stored_data))
    if entities:
        async_add_entities(entities, update_before_add=True)


def _hr_dur(seconds: int) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


class ChaturbateRecordSwitch(SwitchEntity):
    _attr_should_poll = True
    _attr_icon = "mdi:record-rec"

    def __init__(self, hass: HomeAssistant, entry_id: str, model: str, url: str, file_manager, store: Store, stored_data: Dict[str, Any]) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._model = model
        self._url = url
        self._file_manager = file_manager
        
        # Get recording path from file manager
        base_folder = file_manager.get_local_path(model) if file_manager else Path("/tmp")
        self._rec = FFmpegRecorder(url, base_folder.parent, model)
        
        self._store = store
        self._storage_key = f"{entry_id}_{model}"
        
        # Restore state from storage
        saved_state = stored_data.get(self._storage_key, {})
        self._armed = saved_state.get("armed", False)
        
        self._attrs: Dict[str, Any] = {
            ATTR_RECORDING: False,
            ATTR_FILEPATH: None,
            ATTR_PID: None,
            "live": False,
            "last_live_start": saved_state.get("last_live_start"),
            "last_live_end": saved_state.get("last_live_end"),
            "last_stream_duration_sec": saved_state.get("last_stream_duration_sec"),
            "last_stream_duration_hr": saved_state.get("last_stream_duration_hr"),
            "nas_online": False,
            "pending_transfers": 0,
        }
        self._current_stream_start: datetime | None = None
        self._last_completed_file: Path | None = None
        
        # Restore current stream start if it was saved
        if saved_state.get("current_stream_start"):
            try:
                self._current_stream_start = datetime.fromisoformat(saved_state["current_stream_start"])
            except (ValueError, TypeError):
                self._current_stream_start = None
        
        self._attr_name = f"Chaturbate {model} Recording"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{model}_record"

    @property
    def is_on(self) -> bool:
        return self._armed

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._attrs

    async def _get_live_state(self) -> bool:
        data = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {})
        coord = data.get("coordinator")
        if not coord or not getattr(coord, "data", None):
            return False
        st = coord.data.get(self._model)
        return bool(st and getattr(st, "status", None) == "public" and getattr(st, "url", None))

    async def async_update(self) -> None:
        live = await self._get_live_state()
        self._attrs["live"] = live

        running = self._rec.is_running()
        self._attrs[ATTR_RECORDING] = running
        self._attrs[ATTR_PID] = self._rec.pid()

        # Update file manager status
        if self._file_manager:
            self._attrs["nas_online"] = self._file_manager.is_nas_online()
            stats = self._file_manager.get_stats()
            self._attrs["pending_transfers"] = stats.get("pending_files", 0)

        state_changed = False

        if self._armed and live and not running:
            path = await self._rec.start()
            self._attrs[ATTR_FILEPATH] = str(path)
            self._current_stream_start = datetime.now(timezone.utc)
            self._attrs["last_live_start"] = self._current_stream_start.isoformat()
            state_changed = True
        elif (not self._armed or not live) and running:
            # Store the current file before stopping
            if self._rec.current_file:
                self._last_completed_file = Path(self._rec.current_file)
            
            await self._rec.stop()
            self._attrs[ATTR_FILEPATH] = None
            
            if self._current_stream_start:
                end = datetime.now(timezone.utc)
                self._attrs["last_live_end"] = end.isoformat()
                dur = int((end - self._current_stream_start).total_seconds())
                self._attrs["last_stream_duration_sec"] = dur
                self._attrs["last_stream_duration_hr"] = _hr_dur(dur)
                self._current_stream_start = None
                state_changed = True
            
            # Queue file for transfer to NAS if file manager is available
            if self._file_manager and self._last_completed_file and self._last_completed_file.exists():
                await self._file_manager.queue_file_move(self._last_completed_file, self._model)
                _LOGGER.info("Queued recording for NAS transfer: %s", self._last_completed_file)
                self._last_completed_file = None

        # Save state if stream tracking changed
        if state_changed:
            await self._save_state()

        try:
            if self._rec.current_file:
                p = Path(self._rec.current_file)
                if p.exists():
                    sz = p.stat().st_size
                    self._attrs["file_size_gb"] = round(sz / (1024 * 1024 * 1024), 3)
                    self._attrs["file_size_hr"] = (
                        f"{self._attrs['file_size_gb']} GB" if sz >= 1024 * 1024 * 1024 else f"{round(sz / (1024 * 1024), 2)} MB"
                    )
                else:
                    self._attrs.pop("file_size_gb", None)
                    self._attrs.pop("file_size_hr", None)
            else:
                self._attrs.pop("file_size_gb", None)
                self._attrs.pop("file_size_hr", None)
        except OSError as exc:
            _LOGGER.debug("Failed to refresh file stats for %s: %s", self._model, exc)

    async def _save_state(self) -> None:
        """Save the current state to storage."""
        try:
            # Load current data
            data = await self._store.async_load() or {}
            
            # Update this switch's state
            data[self._storage_key] = {
                "armed": self._armed,
                "last_live_start": self._attrs.get("last_live_start"),
                "last_live_end": self._attrs.get("last_live_end"),
                "last_stream_duration_sec": self._attrs.get("last_stream_duration_sec"),
                "last_stream_duration_hr": self._attrs.get("last_stream_duration_hr"),
                "current_stream_start": self._current_stream_start.isoformat() if self._current_stream_start else None,
            }
            
            # Save to storage
            await self._store.async_save(data)
        except Exception as exc:
            _LOGGER.error("Failed to save state for %s: %s", self._model, exc)

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._armed = True
        await self._save_state()
        await self.async_update()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._armed = False
        await self._save_state()
        await self.async_update()
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._entry_id}_{self._model}")},
            "name": f"Chaturbate {self._model}",
            "manufacturer": "CB-Bridge",
            "model": "chaturbate_bridge",
        }
