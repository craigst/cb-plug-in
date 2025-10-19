
from __future__ import annotations
from typing import Any, Dict, List
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .coordinator import ChaturbateCoordinator, ModelState

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coord: ChaturbateCoordinator = data["coordinator"]
    models: List[str] = data["models"]
    entities = [ChaturbateOnlineBinary(coord, entry.entry_id, m) for m in models]
    async_add_entities(entities)

class ChaturbateOnlineBinary(CoordinatorEntity[ChaturbateCoordinator], BinarySensorEntity):
    _attr_device_class = "connectivity"
    _attr_icon = "mdi:webcam"

    def __init__(self, coordinator: ChaturbateCoordinator, entry_id: str, model: str):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._model = model
        self._attr_name = f"Chaturbate {model} Online"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{model}_online"

    @property
    def is_on(self) -> bool:
        st: ModelState | None = self.coordinator.data.get(self._model) if self.coordinator.data else None
        return bool(st and st.status == "public" and st.url)

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, f"{self._entry_id}_{self._model}")},
            "name": f"Chaturbate {self._model}",
            "manufacturer": "CB-Bridge",
            "model": "chaturbate_bridge",
        }
