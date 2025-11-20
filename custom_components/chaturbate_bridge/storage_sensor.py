"""Storage management sensors for Chaturbate Bridge."""
from __future__ import annotations
import logging
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up storage sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    file_manager = data.get("file_manager")
    
    if not file_manager:
        return
    
    entities = [
        StorageManagerSensor(hass, entry.entry_id, file_manager),
    ]
    async_add_entities(entities, update_before_add=True)


class StorageManagerSensor(SensorEntity):
    """Sensor to monitor file manager statistics."""

    _attr_should_poll = True
    _attr_icon = "mdi:harddisk"

    def __init__(self, hass: HomeAssistant, entry_id: str, file_manager) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry_id = entry_id
        self._file_manager = file_manager
        self._attr_name = "Chaturbate Storage Manager"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_storage_manager"
        self._attrs: Dict[str, Any] = {}

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self._file_manager.is_nas_online():
            return "online"
        return "offline"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return self._attrs

    async def async_update(self) -> None:
        """Update the sensor."""
        stats = self._file_manager.get_stats()
        
        self._attrs = {
            "nas_status": "online" if stats["nas_online"] else "offline",
            "pending_files": stats["pending_files"],
            "total_moved": stats["total_moved"],
            "total_moved_gb": round(stats["total_moved_bytes"] / (1024 ** 3), 2) if stats["total_moved_bytes"] else 0,
            "failed_moves": stats["failed_moves"],
            "last_move_time": stats["last_move_time"],
            "local_path": stats["local_path"],
            "remote_path": stats["remote_path"],
            "auto_move_enabled": stats["auto_move_enabled"],
        }

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._entry_id}_storage")},
            "name": "Chaturbate Storage Manager",
            "manufacturer": "CB-Bridge",
            "model": "Storage Manager",
        }
