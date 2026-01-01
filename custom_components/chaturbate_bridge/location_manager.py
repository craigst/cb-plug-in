"""Location management utilities for Chaturbate Bridge."""

from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "chaturbate_bridge_locations"

class LocationManager:
    """Manages recording locations with validation and browsing."""
    
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._locations: Dict[str, Dict] = {}
        
    async def async_load(self) -> None:
        """Load saved locations."""
        data = await self._store.async_load() or {}
        self._locations = data.get("locations", {})
        
    async def async_save(self) -> None:
        """Save locations to storage."""
        await self._store.async_save({"locations": self._locations})
        
    async def async_validate_location(self, path: str) -> Tuple[bool, str]:
        """Validate a recording location."""
        try:
            location = Path(path)
            
            # Check if path exists or can be created
            if not location.exists():
                try:
                    location.mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError) as exc:
                    return False, f"Cannot create directory: {exc}"
            
            # Check write permissions
            test_file = location / ".chaturbate_bridge_write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError) as exc:
                return False, f"No write permission: {exc}"
            
            # Check available space
            stat = location.statvfs()
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            if free_gb < 1:  # Less than 1GB free
                return False, f"Insufficient space: {free_gb:.1f}GB available"
            
            return True, f"Valid location ({free_gb:.1f}GB free)"
            
        except Exception as exc:
            return False, f"Validation error: {exc}"
    
    async def async_get_available_locations(self) -> List[Dict[str, str]]:
        """Get list of available recording locations."""
        locations = []
        
        # Standard HA media directories
        media_dirs = [
            "/media",
            "/config/media", 
            "/config/www/media",
            "/share/media",
            "/tmp/media"
        ]
        
        for path in media_dirs:
            is_valid, message = await self.async_validate_location(path)
            if is_valid:
                locations.append({
                    "path": path,
                    "name": path.split("/")[-1] or path,
                    "description": message
                })
        
        # Add saved custom locations
        for loc_id, loc_data in self._locations.items():
            if loc_data.get("path"):
                is_valid, message = await self.async_validate_location(loc_data["path"])
                if is_valid:
                    locations.append({
                        "path": loc_data["path"],
                        "name": loc_data.get("name", loc_data["path"]),
                        "description": f"Custom location - {message}"
                    })
        
        return locations
    
    async def async_add_custom_location(self, name: str, path: str) -> Tuple[bool, str]:
        """Add a custom recording location."""
        is_valid, message = await self.async_validate_location(path)
        if not is_valid:
            return False, message
        
        loc_id = name.lower().replace(" ", "_")
        self._locations[loc_id] = {
            "name": name,
            "path": path,
            "added_at": asyncio.get_event_loop().time()
        }
        await self.async_save()
        
        _LOGGER.info("Added custom location: %s -> %s", name, path)
        return True, "Location added successfully"
    
    async def async_remove_location(self, loc_id: str) -> Tuple[bool, str]:
        """Remove a custom location."""
        if loc_id in self._locations:
            del self._locations[loc_id]
            await self.async_save()
            _LOGGER.info("Removed custom location: %s", loc_id)
            return True, "Location removed successfully"
        return False, "Location not found"
    
    async def async_get_location_stats(self, path: str) -> Dict[str, any]:
        """Get statistics for a location."""
        try:
            location = Path(path)
            if not location.exists():
                return {"error": "Location does not exist"}
            
            # Count files and sizes
            total_files = 0
            total_size = 0
            mkv_files = 0
            mp4_files = 0
            
            for file_path in location.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    size = file_path.stat().st_size
                    total_size += size
                    
                    if file_path.suffix.lower() == ".mkv":
                        mkv_files += 1
                    elif file_path.suffix.lower() == ".mp4":
                        mp4_files += 1
            
            # Get disk space
            stat = location.statvfs()
            free_space = stat.f_bavail * stat.f_frsize
            total_space = stat.f_blocks * stat.f_frsize
            
            return {
                "total_files": total_files,
                "total_size_gb": round(total_size / (1024**3), 2),
                "mkv_files": mkv_files,
                "mp4_files": mp4_files,
                "free_space_gb": round(free_space / (1024**3), 2),
                "total_space_gb": round(total_space / (1024**3), 2),
                "usage_percent": round(((total_space - free_space) / total_space) * 100, 1)
            }
            
        except Exception as exc:
            return {"error": f"Stats error: {exc}"}