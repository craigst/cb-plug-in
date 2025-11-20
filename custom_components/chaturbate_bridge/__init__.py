
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
    DEFAULT_LOCAL_RECORD_PATH,
    DEFAULT_REMOTE_RECORD_PATH,
    DEFAULT_ENABLE_AUTO_MOVE,
    DEFAULT_NAS_CHECK_INTERVAL,
    DEFAULT_AUTO_CLEANUP,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_MIN_FREE_SPACE_GB,
)
from .coordinator import ChaturbateCoordinator
from .file_manager import FileManager

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

    # Get storage configuration
    local_record_path = entry.options.get("local_record_path", entry.data.get("local_record_path", DEFAULT_LOCAL_RECORD_PATH))
    remote_record_path = entry.options.get("remote_record_path", entry.data.get("remote_record_path", DEFAULT_REMOTE_RECORD_PATH))
    enable_auto_move = entry.options.get("enable_auto_move", entry.data.get("enable_auto_move", DEFAULT_ENABLE_AUTO_MOVE))
    nas_check_interval = entry.options.get("nas_check_interval", entry.data.get("nas_check_interval", DEFAULT_NAS_CHECK_INTERVAL))
    auto_cleanup = entry.options.get("auto_cleanup", entry.data.get("auto_cleanup", DEFAULT_AUTO_CLEANUP))
    retention_days = entry.options.get("retention_days", entry.data.get("retention_days", DEFAULT_RETENTION_DAYS))
    min_free_space_gb = entry.options.get("min_free_space_gb", entry.data.get("min_free_space_gb", DEFAULT_MIN_FREE_SPACE_GB))

    coord = ChaturbateCoordinator(
        hass, models, scan_interval, go2rtc_url, mode,
        public_go2rtc_base=public_go2rtc_base,
        expose_variants=expose_variants
    )
    await coord.async_config_entry_first_refresh()

    # Initialize file manager
    file_manager = FileManager(
        hass,
        local_record_path,
        remote_record_path,
        enable_auto_move=enable_auto_move,
        nas_check_interval=nas_check_interval,
        auto_cleanup=auto_cleanup,
        retention_days=retention_days,
        min_free_space_gb=min_free_space_gb,
    )
    await file_manager.async_start()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coord,
        "file_manager": file_manager,
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
    if data:
        if "coordinator" in data:
            await data["coordinator"].async_close()
        if "file_manager" in data:
            await data["file_manager"].async_stop()
    return unload_ok

async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Reload the entry when options change
    await hass.config_entries.async_reload(entry.entry_id)
