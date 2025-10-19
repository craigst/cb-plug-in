
from __future__ import annotations
import asyncio
import logging
from typing import List, Optional, Dict, Set
import aiohttp, urllib.parse
from urllib.parse import urlparse, quote

from homeassistant.components.camera import Camera, StreamType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_EXPOSE_VARIANTS,
    DEFAULT_GO2RTC_URL,
    DEFAULT_PUBLIC_GO2RTC_BASE,
    DOMAIN,
)
from .coordinator import ChaturbateCoordinator, ModelState

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coord: ChaturbateCoordinator = data["coordinator"]
    models: List[str] = data["models"]
    expose_variants: bool = data.get("expose_variants", DEFAULT_EXPOSE_VARIANTS)
    base_source = data.get("public_go2rtc_base") or data.get("go2rtc_url") or DEFAULT_PUBLIC_GO2RTC_BASE or DEFAULT_GO2RTC_URL
    public_base = base_source.rstrip("/")

    # Storage for dynamic cameras
    data.setdefault("camera_entities", {})   # alias -> entity
    data.setdefault("camera_known", set())   # aliases we've created
    entities_by_alias: Dict[str, CBCamera] = data["camera_entities"]
    known: Set[str] = data["camera_known"]

    def desired_aliases() -> Dict[str, Dict[str, str]]:
        wants: Dict[str, Dict[str, str]] = {}
        if not coord.data:
            return wants
        for m in models:
            st: Optional[ModelState] = coord.data.get(m)
            if not st or st.status != "public":
                continue
            # always include "best" alias == model
            wants[m] = {"model": m, "alias": m, "title": f"{m} (best)"}
            if expose_variants and st.variant_stream_names:
                for name in st.variant_stream_names:
                    if name not in wants:
                        suffix = name.replace(f"{m}_", "")
                        wants[name] = {"model": m, "alias": name, "title": f"{m} {suffix}"}
        return wants

    # Initial add: only live aliases
    to_add: List[CBCamera] = []
    for alias, meta in desired_aliases().items():
        if alias not in known:
            ent = CBCamera(coord, entry.entry_id, meta["model"], public_base, alias=alias, title=meta["title"])
            entities_by_alias[alias] = ent
            known.add(alias)
            to_add.append(ent)
    if to_add:
        async_add_entities(to_add, update_before_add=True)

    @callback
    def _on_coordinator_update():
        wants = desired_aliases()
        # Add new ones
        new_entities: List[CBCamera] = []
        for alias, meta in wants.items():
            if alias not in known:
                ent = CBCamera(coord, entry.entry_id, meta["model"], public_base, alias=alias, title=meta["title"])
                entities_by_alias[alias] = ent
                known.add(alias)
                new_entities.append(ent)
        if new_entities:
            async_add_entities(new_entities, update_before_add=True)

        # Remove those no longer desired (model offline or variants disappeared)
        to_remove = [a for a in list(known) if a not in wants]
        for alias in to_remove:
            ent = entities_by_alias.pop(alias, None)
            if ent:
                # schedule entity removal to avoid blocking update loop
                hass.async_create_task(ent.async_remove())
            known.discard(alias)

    coord.async_add_listener(_on_coordinator_update)

class CBCamera(CoordinatorEntity[ChaturbateCoordinator], Camera):
    def __init__(self, coordinator: ChaturbateCoordinator, entry_id: str, model: str, base: str, *, alias: str, title: str) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._entry_id = entry_id
        self._model = model
        self._alias = alias
        self._title = title
        self._base = base
        self._attr_name = f"CB {title}"
        self._attr_unique_id = f"cb_cam_{entry_id}_{alias}"

    @property
    def available(self) -> bool:
        st: Optional[ModelState] = self.coordinator.data.get(self._model) if self.coordinator.data else None
        return bool(st and st.status == "public")

    @property
    def frontend_stream_type(self) -> StreamType | None:
        # Let HA stream component pick it up; we provide RTSP; HA can transcode to HLS
        return None

    async def stream_source(self) -> str | None:
        p = urlparse(self._base)
        host = p.hostname or "127.0.0.1"
        return f"rtsp://{host}:8554/{quote(self._alias, safe='')}"

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        url = f"{self._base}/api/frame.jpeg?src={urllib.parse.quote(self._alias, safe='')}"
        if width:
            url += f"&width={int(width)}"
        if height:
            url += f"&height={int(height)}"
        try:
            session: aiohttp.ClientSession = self.coordinator.session
            async with session.get(url, timeout=self.coordinator.request_timeout) as r:
                if r.status == 200:
                    return await r.read()
                _LOGGER.warning("Snapshot fetch for %s returned status %s", self._alias, r.status)
        except asyncio.TimeoutError:
            _LOGGER.warning("Snapshot fetch timed out for %s", self._alias)
        except aiohttp.ClientError as exc:
            _LOGGER.warning("Snapshot fetch failed for %s: %s", self._alias, exc)
        except Exception as exc:
            _LOGGER.error("Unexpected snapshot error for %s: %s", self._alias, exc, exc_info=True)
        return None

    @property
    def device_info(self) -> Dict[str, str]:
        return {
            "identifiers": {(DOMAIN, f"{self._entry_id}_{self._model}")},
            "name": f"Chaturbate {self._model}",
            "manufacturer": "CB-Bridge",
            "model": "chaturbate_bridge",
        }
