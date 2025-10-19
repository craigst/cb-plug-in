
from __future__ import annotations
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import (
    DOMAIN,
    INTEGRATION_VERSION,
    DEFAULT_GO2RTC_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MODE,
    DEFAULT_RECORD_BASE,
    DEFAULT_PUBLIC_GO2RTC_BASE,
    DEFAULT_EXPOSE_VARIANTS,
)
from .coordinator import ChaturbateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.CAMERA, Platform.SWITCH]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    models = entry.options.get("models", entry.data.get("models", []))
    go2rtc_url = entry.data.get("go2rtc_url", DEFAULT_GO2RTC_URL)
    scan_interval = entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    mode = entry.data.get("mode", DEFAULT_MODE)
    public_go2rtc_base = entry.data.get("public_go2rtc_base") or go2rtc_url or DEFAULT_PUBLIC_GO2RTC_BASE
    expose_variants = entry.data.get("expose_variants", DEFAULT_EXPOSE_VARIANTS)

    coord = ChaturbateCoordinator(
        hass, models, scan_interval, go2rtc_url, mode,
        public_go2rtc_base=public_go2rtc_base,
        expose_variants=expose_variants
    )
    await coord.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coord,
        "models": models,
        "go2rtc_url": go2rtc_url,
        "scan_interval": scan_interval,
        "mode": mode,
        "record_base": entry.data.get("record_base", DEFAULT_RECORD_BASE),
        "public_go2rtc_base": public_go2rtc_base,
        "expose_variants": expose_variants,
        "camera_created": set(),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_listener))
    _LOGGER.info("Chaturbate Bridge v%s set up with models: %s; go2rtc=%s",
                 INTEGRATION_VERSION, models, go2rtc_url)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data and "coordinator" in data:
        await data["coordinator"].async_close()
    return unload_ok

async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]
    new_models = entry.options.get("models", entry.data.get("models", []))
    data["models"] = new_models
    coord.models = new_models
    await coord.async_request_refresh()
