"""Test configuration for Chaturbate Bridge."""

from __future__ import annotations
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.chaturbate_bridge import (
    async_setup_entry,
    async_unload_entry,
    DOMAIN,
)
from custom_components.chaturbate_bridge.coordinator import ChaturbateCoordinator
from custom_components.chaturbate_bridge.file_manager import FileManager
from custom_components.chaturbate_bridge.location_manager import LocationManager

@pytest.fixture
async def hass() -> HomeAssistant:
    """Create a Home Assistant instance for testing."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config.path = MagicMock(return_value="/config")
    return hass

@pytest.fixture
async def config_entry() -> ConfigEntry:
    """Create a config entry for testing."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.data = {
        "go2rtc_url": "http://127.0.0.1:1984",
        "models": ["test_model"],
        "scan_interval": 30,
        "mode": "plain",
        "record_base": "media",
        "expose_variants": True,
    }
    entry.options = {}
    entry.async_on_unload = MagicMock()
    return entry

@pytest.fixture
def aiohttp_session():
    """Mock aiohttp session."""
    return AsyncMock()

@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Test setting up the integration."""
    result = await async_setup_entry(hass, config_entry)
    
    assert result is True
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    assert "coordinator" in data
    assert "file_manager" in data
    assert isinstance(data["coordinator"], ChaturbateCoordinator)
    assert isinstance(data["file_manager"], FileManager)

@pytest.mark.asyncio
async def test_async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Test unloading the integration."""
    # Setup first
    await async_setup_entry(hass, config_entry)
    
    # Then unload
    result = await async_unload_entry(hass, config_entry)
    
    assert result is True
    assert config_entry.entry_id not in hass.data[DOMAIN]

class TestChaturbateCoordinator:
    """Test coordinator functionality."""
    
    @pytest.mark.asyncio
    async def test_coordinator_init(self, aiohttp_session) -> None:
        """Test coordinator initialization."""
        coordinator = ChaturbateCoordinator(
            hass=MagicMock(),
            models=["test_model"],
            scan_interval=30,
            go2rtc_url="http://127.0.0.1:1984",
            mode="plain"
        )
        
        assert coordinator.models == ["test_model"]
        assert coordinator.go2rtc_url == "http://127.0.0.1:1984"
        assert coordinator.mode == "plain"
        assert coordinator.expose_variants is True

class TestFileManager:
    """Test file manager functionality."""
    
    @pytest.mark.asyncio
    async def test_file_manager_init(self, hass: HomeAssistant) -> None:
        """Test file manager initialization."""
        file_manager = FileManager(
            hass=hass,
            local_path="/tmp/test",
            remote_path="",
            enable_auto_move=False,
            nas_check_interval=60,
            auto_cleanup=False,
            retention_days=30,
            min_free_space_gb=10,
        )
        
        assert file_manager.local_path == Path("/tmp/test")
        assert file_manager.remote_path == Path("")
        assert file_manager.enable_auto_move is False

class TestLocationManager:
    """Test location manager functionality."""
    
    @pytest.mark.asyncio
    async def test_location_manager_init(self, hass: HomeAssistant) -> None:
        """Test location manager initialization."""
        location_manager = LocationManager(hass)
        assert location_manager.hass == hass
        assert location_manager._locations == {}
    
    @pytest.mark.asyncio
    async def test_validate_location_success(self, location_manager: LocationManager, tmp_path: Path) -> None:
        """Test successful location validation."""
        test_path = str(tmp_path / "valid_location")
        
        is_valid, message = await location_manager.async_validate_location(test_path)
        
        assert is_valid is True
        assert "Valid location" in message
    
    @pytest.mark.asyncio
    async def test_validate_location_invalid(self, location_manager: LocationManager) -> None:
        """Test invalid location validation."""
        is_valid, message = await location_manager.async_validate_location("/nonexistent/invalid/path")
        
        assert is_valid is False
        assert "Validation error" in message or "does not exist" in message