
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

from .const import (
    DEFAULT_GO2RTC_URL,
    DEFAULT_PUBLIC_GO2RTC_BASE,
    DEFAULT_RECORD_BASE,
    DOMAIN,
)
from .recorder import FFmpegRecorder

_LOGGER = logging.getLogger(__name__)

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
    record_base: str = entry.options.get("record_base", data.get("record_base", DEFAULT_RECORD_BASE))
    base_source = data.get("public_go2rtc_base") or data.get("go2rtc_url") or DEFAULT_PUBLIC_GO2RTC_BASE or DEFAULT_GO2RTC_URL
    public_base: str = base_source.rstrip("/")

    parsed = urlparse(public_base)
    host = parsed.hostname or "127.0.0.1"
    rtsp_base = f"rtsp://{host}:8554"

    base_folder = _resolve_base_folder(hass, record_base)

    entities: List[ChaturbateRecordSwitch] = []
    for m in models:
        url = f"{rtsp_base}/{quote(m, safe='')}"
        entities.append(ChaturbateRecordSwitch(hass, entry.entry_id, m, url, base_folder))
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

    def __init__(self, hass: HomeAssistant, entry_id: str, model: str, url: str, base_folder: Path) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._model = model
        self._url = url
        self._rec = FFmpegRecorder(url, base_folder, model)
        self._armed = False  # ON = monitor & auto-record when live
        self._attrs: Dict[str, Any] = {
            ATTR_RECORDING: False,
            ATTR_FILEPATH: None,
            ATTR_PID: None,
            "live": False,
            "last_live_start": None,
            "last_live_end": None,
            "last_stream_duration_sec": None,
            "last_stream_duration_hr": None,
        }
        self._current_stream_start: datetime | None = None
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

        if self._armed and live and not running:
            path = await self._rec.start()
            self._attrs[ATTR_FILEPATH] = str(path)
            self._current_stream_start = datetime.now(timezone.utc)
            self._attrs["last_live_start"] = self._current_stream_start.isoformat()
        elif (not self._armed or not live) and running:
            await self._rec.stop()
            self._attrs[ATTR_FILEPATH] = None
            if self._current_stream_start:
                end = datetime.now(timezone.utc)
                self._attrs["last_live_end"] = end.isoformat()
                dur = int((end - self._current_stream_start).total_seconds())
                self._attrs["last_stream_duration_sec"] = dur
                self._attrs["last_stream_duration_hr"] = _hr_dur(dur)
                self._current_stream_start = None

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._armed = True
        await self.async_update()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._armed = False
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
