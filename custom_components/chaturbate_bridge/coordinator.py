
from __future__ import annotations
import logging, asyncio, json, re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import aiohttp
from datetime import timedelta
from time import time as _now
from urllib.parse import urljoin

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CB_EDGE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_PREFERRED_QUALITY,
    GO2RTC_STREAM_ENDPOINT,
    INTEGRATION_TITLE,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

@dataclass
class Variant:
    bandwidth: int
    resolution: str
    url: str

@dataclass
class ModelState:
    status: str = "offline"
    url: str | None = None
    title: str | None = None
    viewer_count: int | None = None
    last_changed: float | None = None
    variants: List[Variant] | None = None
    variant_stream_names: List[str] | None = None

class ChaturbateCoordinator(DataUpdateCoordinator[Dict[str, ModelState]]):
    def __init__(self, hass: HomeAssistant, models: List[str], scan_interval: int,
                 go2rtc_url: str, mode: str,
                 public_go2rtc_base: str = "",
                 expose_variants: bool = True):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=INTEGRATION_TITLE,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.models = models
        self.go2rtc_url = go2rtc_url.rstrip("/")
        self.mode = mode
        self.public_go2rtc_base = public_go2rtc_base.rstrip("/") if public_go2rtc_base else ""
        self.expose_variants = expose_variants
        self.preferred_quality = DEFAULT_PREFERRED_QUALITY
        self._timeout: aiohttp.ClientTimeout | None = None
        self._session: aiohttp.ClientSession | None = None
        self._last_status: Dict[str, str] = {}
        self._active_streams: Dict[str, List[str]] = {}
        self._streams_endpoint = f"{self.go2rtc_url}{GO2RTC_STREAM_ENDPOINT}"

    async def async_setup(self):
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        self._session = async_get_clientsession(self.hass)
        self._timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)

    @property
    def request_timeout(self) -> aiohttp.ClientTimeout:
        """Return the configured aiohttp timeout."""
        return self._timeout

    @property
    def session(self) -> aiohttp.ClientSession:
        """Return the shared aiohttp session."""
        return self._session

    async def _async_update_data(self) -> Dict[str, ModelState]:
        results: Dict[str, ModelState] = {}
        tasks = [self._fetch_one(m) for m in self.models]
        for model, state in await asyncio.gather(*tasks):
            results[model] = state
            prev = self._last_status.get(model)
            self._last_status[model] = state.status
            if state.status == "public" and state.url:
                variants = await self._fetch_variants(state.url, model)
                state.variants = variants
                names = await self._upsert_variants(model, variants)
                state.variant_stream_names = names
                if variants:
                    best_variant = variants[-1]
                    await self._upsert_alias_from_variant(model, best_variant)
                    if model not in names:
                        names.append(model)
                    self._active_streams[model] = names
            else:
                if prev == "public" and state.status != "public":
                    await self._cleanup_model_streams(model)
                    state.variants = None
                    state.variant_stream_names = None
        return results

    async def _fetch_one(self, model: str) -> Tuple[str, ModelState]:
        data = f"room_slug={model}"
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        }
        js = {}
        try:
            async with self._session.post(CB_EDGE_URL, headers=headers, data=data, timeout=self._timeout) as r:
                if r.status != 200:
                    _LOGGER.warning("Fetch for %s returned status %s", model, r.status)
                txt = await r.text()
                try:
                    js = await r.json(content_type=None)
                except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
                    _LOGGER.debug("Non-JSON for %s (%s): %s", model, err, txt[:200])
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            _LOGGER.warning("Fetch error for %s: %s", model, exc)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Unexpected fetch error for %s: %s", model, exc, exc_info=True)
        st = ModelState()
        st.status = js.get("room_status", "offline")
        st.url = js.get("url")
        st.title = js.get("title")
        st.viewer_count = js.get("viewer_count")
        st.last_changed = _now()
        return model, st

    async def _fetch_variants(self, master_url: str, model: str) -> List[Variant]:
        headers = {"User-Agent": USER_AGENT, "Referer": f"https://chaturbate.com/{model}/"}
        try:
            async with self._session.get(master_url, headers=headers, timeout=self._timeout) as r:
                if r.status != 200:
                    _LOGGER.warning("Variant manifest for %s returned status %s", model, r.status)
                text = await r.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            _LOGGER.warning("Variant fetch failed for %s: %s", model, exc)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Unexpected error fetching variants for %s: %s", model, exc, exc_info=True)
            return []
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        variants: List[Variant] = []
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF:"):
                attrs = line.split(":",1)[1]
                import re
                bwm = re.search(r"BANDWIDTH=([0-9]+)", attrs)
                rem = re.search(r'RESOLUTION=([^,]+)', attrs)
                bw = int(bwm.group(1)) if bwm else 0
                res = rem.group(1) if rem else ""
                if i+1 < len(lines):
                    vurl = lines[i+1]
                    if not vurl.startswith("#"):
                        absurl = urljoin(master_url, vurl)
                        variants.append(Variant(bw, res, absurl))
        if self.preferred_quality == "best":
            variants.sort(key=lambda v: (-v.bandwidth, -_res_to_num(v.resolution)))
        else:
            target = _res_to_num(self.preferred_quality)
            variants.sort(key=lambda v: (abs(_res_to_num(v.resolution) - target), -v.bandwidth))
        return variants

    async def _upsert_variants(self, model: str, variants: List[Variant]) -> List[str]:
        names: List[str] = []
        ref = f"https://chaturbate.com/{model}/"
        for v in variants:
            suffix = _suffix_from_res(v.resolution) or f"{v.bandwidth//1000}k"
            name = f"{model}_{suffix}"
            names.append(name)
            if self.mode == "plain":
                src = f"{v.url}#header=Referer:{ref}#header=User-Agent:Mozilla/5.0"
            else:
                src = (f"ffmpeg:{v.url}#video=copy#audio=aac"
                       f"#input=-headers 'Referer: {ref}\r\nUser-Agent: Mozilla/5.0' -re -i {{input}}")
            await self._upsert_go2rtc(name, src)
        return names

    async def _upsert_alias_from_variant(self, alias: str, variant: Variant):
        ref = f"https://chaturbate.com/{alias}/"
        if self.mode == "plain":
            src = f"{variant.url}#header=Referer:{ref}#header=User-Agent:Mozilla/5.0"
        else:
            src = (f"ffmpeg:{variant.url}#video=copy#audio=aac"
                   f"#input=-headers 'Referer: {ref}\r\nUser-Agent: Mozilla/5.0' -re -i {{input}}")
        await self._upsert_go2rtc(alias, src)

    async def _upsert_go2rtc(self, name: str, src: str):
        q = f"{self._streams_endpoint}?name={name}&src={src}"
        try:
            async with self._session.put(q, timeout=self._timeout) as r:
                body = await r.text()
                if r.status >= 400:
                    _LOGGER.error(
                        "go2rtc upsert for %s failed (%s): %s",
                        name,
                        r.status,
                        body,
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            _LOGGER.warning("Failed to upsert go2rtc stream %s: %s", name, exc)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Unexpected go2rtc upsert error for %s: %s", name, exc, exc_info=True)

    async def _cleanup_model_streams(self, model: str):
        for name in self._active_streams.get(model, []):
            q = f"{self._streams_endpoint}?src={name}"
            try:
                async with self._session.delete(q, timeout=self._timeout) as r:
                    body = await r.text()
                    if r.status >= 400:
                        _LOGGER.warning(
                            "go2rtc removal for %s failed (%s): %s",
                            name,
                            r.status,
                            body,
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                _LOGGER.warning("Failed to remove go2rtc stream %s: %s", name, exc)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error("Unexpected go2rtc removal error for %s: %s", name, exc, exc_info=True)
        self._active_streams[model] = []

    async def async_close(self):
        if not self._session.closed:
            try:
                await self._session.close()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("Error closing aiohttp session: %s", exc, exc_info=True)

def _suffix_from_res(res: str) -> Optional[str]:
    if "x" in res:
        try:
            w,h = res.split("x")
            return f"{int(h)}p"
        except (TypeError, ValueError):
            return None
    return None

def _res_key(res: str):
    if "x" in res:
        try:
            w,h = res.split("x")
            return int(h)
        except (TypeError, ValueError):
            return 0
    return 0

def _res_to_num(res: str) -> int:
    m = re.search(r'(\d+)p?', res)
    return int(m.group(1)) if m else 0
