
from __future__ import annotations
from typing import Any, Dict, List
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from .coordinator import ChaturbateCoordinator, ModelState, Variant

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coord: ChaturbateCoordinator = data["coordinator"]
    models: List[str] = data["models"]
    entities = [ChaturbateStatusSensor(coord, entry.entry_id, m) for m in models]
    async_add_entities(entities)

class ChaturbateStatusSensor(CoordinatorEntity[ChaturbateCoordinator], SensorEntity):
    _attr_icon = "mdi:webcam"

    def __init__(self, coordinator: ChaturbateCoordinator, entry_id: str, model: str):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._model = model
        self._attr_name = f"Chaturbate {model} Status"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{model}_status"

    @property
    def native_value(self) -> str:
        st: ModelState | None = self.coordinator.data.get(self._model) if self.coordinator.data else None
        return st.status if st else "unknown"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        st: ModelState | None = self.coordinator.data.get(self._model) if self.coordinator.data else None
        if not st:
            return {}
        attrs: Dict[str, Any] = {
            "url": st.url,
            "title": st.title,
            "viewer_count": st.viewer_count,
            "last_changed": st.last_changed,
        }
        if st.variants:
            attrs["variants"] = [
                {"bandwidth": v.bandwidth, "resolution": v.resolution, "url": v.url}
                for v in st.variants
            ]
        if st.variant_stream_names:
            attrs["variant_stream_names"] = st.variant_stream_names
        return attrs

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._entry_id}_{self._model}")},
            "name": f"Chaturbate {self._model}",
            "manufacturer": "CB-Bridge",
            "model": "chaturbate_bridge",
        }
