"""Web UI for Chaturbate Bridge management."""

from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, INTEGRATION_VERSION

_LOGGER = logging.getLogger(__name__)

class ChaturbateBridgeWebView(HomeAssistantView):
    """Web view for Chaturbate Bridge management."""
    
    url = "/api/chaturbate_bridge"
    name = "api:chaturbate_bridge"
    requires_auth = True
    
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        
    async def get(self, request) -> Any:
        """Handle GET request."""
        return await self._serve_html()
    
    async def post(self, request) -> Any:
        """Handle POST request for API calls."""
        try:
            data = await request.json()
            action = data.get("action")
            
            if action == "get_status":
                return await self._get_status()
            elif action == "get_models":
                return await self._get_models()
            elif action == "get_recordings":
                return await self._get_recordings(data.get("model"))
            elif action == "get_locations":
                return await self._get_locations()
            elif action == "add_location":
                return await self._add_location(data.get("name"), data.get("path"))
            elif action == "remove_location":
                return await self._remove_location(data.get("location_id"))
            elif action == "get_logs":
                return await self._get_logs(data.get("level", "INFO"))
            else:
                return {"error": "Unknown action"}
                
        except Exception as exc:
            _LOGGER.error("Web UI API error: %s", exc)
            return {"error": str(exc)}
    
    async def _serve_html(self) -> Any:
        """Serve the HTML interface."""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chaturbate Bridge Manager</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a1a; color: #fff; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 1.1em; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #2a2a2a; border-radius: 15px; padding: 25px; border: 1px solid #3a3a3a; }
        .card h2 { margin-bottom: 20px; color: #667eea; font-size: 1.5em; }
        .status-item { display: flex; justify-content: space-between; margin-bottom: 15px; padding: 10px; background: #1a1a1a; border-radius: 8px; }
        .status-item.online { border-left: 4px solid #4caf50; }
        .status-item.offline { border-left: 4px solid #f44336; }
        .btn { background: #667eea; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 1em; transition: all 0.3s; }
        .btn:hover { background: #5a6fd8; transform: translateY(-2px); }
        .btn.danger { background: #f44336; }
        .btn.danger:hover { background: #da190b; }
        .btn.success { background: #4caf50; }
        .btn.success:hover { background: #45a049; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 500; }
        .form-group input, .form-group select { width: 100%; padding: 12px; background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 8px; color: white; font-size: 1em; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: #667eea; }
        .log-container { background: #1a1a1a; border-radius: 8px; padding: 15px; height: 300px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.9em; }
        .log-entry { margin-bottom: 5px; padding: 5px; border-radius: 3px; }
        .log-entry.info { background: rgba(33, 150, 243, 0.1); }
        .log-entry.warning { background: rgba(255, 152, 0, 0.1); }
        .log-entry.error { background: rgba(244, 67, 54, 0.1); }
        .recording-item { background: #1a1a1a; border-radius: 8px; padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .recording-info h4 { margin-bottom: 5px; }
        .recording-info p { opacity: 0.7; font-size: 0.9em; }
        .video-player { width: 100%; border-radius: 8px; background: #000; }
        .tabs { display: flex; margin-bottom: 20px; border-bottom: 1px solid #3a3a3a; }
        .tab { padding: 15px 25px; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.3s; }
        .tab.active { border-bottom-color: #667eea; color: #667eea; }
        .tab:hover { background: #2a2a2a; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .stat-card { background: #1a1a1a; border-radius: 8px; padding: 20px; text-align: center; }
        .stat-card h3 { font-size: 2em; margin-bottom: 5px; color: #667eea; }
        .stat-card p { opacity: 0.7; }
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 2em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 Chaturbate Bridge Manager</h1>
            <p>Version """ + INTEGRATION_VERSION + """ - Professional stream recording management</p>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('dashboard')">Dashboard</div>
            <div class="tab" onclick="showTab('models')">Models</div>
            <div class="tab" onclick="showTab('recordings')">Recordings</div>
            <div class="tab" onclick="showTab('locations')">Locations</div>
            <div class="tab" onclick="showTab('logs')">Logs</div>
        </div>
        
        <div id="dashboard" class="tab-content active">
            <div class="grid">
                <div class="card">
                    <h2>📊 System Status</h2>
                    <div id="system-status"></div>
                </div>
                <div class="card">
                    <h2>🎬 Recording Stats</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h3 id="total-recordings">0</h3>
                            <p>Total Recordings</p>
                        </div>
                        <div class="stat-card">
                            <h3 id="active-recordings">0</h3>
                            <p>Active</p>
                        </div>
                        <div class="stat-card">
                            <h3 id="storage-used">0GB</h3>
                            <p>Storage Used</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="models" class="tab-content">
            <div class="card">
                <h2>👥 Model Status</h2>
                <div id="models-list"></div>
            </div>
        </div>
        
        <div id="recordings" class="tab-content">
            <div class="card">
                <h2>📹 Recent Recordings</h2>
                <div class="form-group">
                    <label>Filter by Model:</label>
                    <select id="recording-filter" onchange="loadRecordings()">
                        <option value="">All Models</option>
                    </select>
                </div>
                <div id="recordings-list"></div>
            </div>
        </div>
        
        <div id="locations" class="tab-content">
            <div class="card">
                <h2>📁 Storage Locations</h2>
                <div class="form-group">
                    <label>Add Custom Location:</label>
                    <div style="display: flex; gap: 10px;">
                        <input type="text" id="location-name" placeholder="Location name">
                        <input type="text" id="location-path" placeholder="/path/to/location" style="flex: 1;">
                        <button class="btn" onclick="addLocation()">Add</button>
                    </div>
                </div>
                <div id="locations-list"></div>
            </div>
        </div>
        
        <div id="logs" class="tab-content">
            <div class="card">
                <h2>📋 System Logs</h2>
                <div class="form-group">
                    <label>Log Level:</label>
                    <select id="log-level" onchange="loadLogs()">
                        <option value="INFO">Info</option>
                        <option value="WARNING">Warning</option>
                        <option value="ERROR">Error</option>
                    </select>
                </div>
                <div class="log-container" id="logs-container"></div>
            </div>
        </div>
    </div>
    
    <script>
        let currentData = {};
        
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
            
            if (tabName === 'dashboard') loadDashboard();
            if (tabName === 'models') loadModels();
            if (tabName === 'recordings') loadRecordings();
            if (tabName === 'locations') loadLocations();
            if (tabName === 'logs') loadLogs();
        }
        
        async function apiCall(action, data = {}) {
            try {
                const response = await fetch('/api/chaturbate_bridge', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action, ...data })
                });
                return await response.json();
            } catch (error) {
                console.error('API call failed:', error);
                return { error: error.message };
            }
        }
        
        async function loadDashboard() {
            const status = await apiCall('get_status');
            if (!status.error) {
                document.getElementById('system-status').innerHTML = status.items.map(item => 
                    `<div class="status-item ${item.online ? 'online' : 'offline'}">
                        <span>${item.name}</span>
                        <span>${item.online ? '🟢 Online' : '🔴 Offline'}</span>
                    </div>`
                ).join('');
                
                document.getElementById('total-recordings').textContent = status.stats.total_recordings || 0;
                document.getElementById('active-recordings').textContent = status.stats.active_recordings || 0;
                document.getElementById('storage-used').textContent = (status.stats.storage_used_gb || 0) + 'GB';
            }
        }
        
        async function loadModels() {
            const models = await apiCall('get_models');
            if (!models.error) {
                document.getElementById('models-list').innerHTML = models.map(model => 
                    `<div class="status-item ${model.online ? 'online' : 'offline'}">
                        <div>
                            <strong>${model.name}</strong>
                            ${model.title ? `<br><small>${model.title}</small>` : ''}
                            ${model.viewer_count ? `<br><small>👁 ${model.viewer_count} viewers</small>` : ''}
                        </div>
                        <div>
                            ${model.online ? `<button class="btn success" onclick="toggleRecording('${model.name}', true)">Record</button>` : ''}
                            ${model.recording ? `<button class="btn danger" onclick="toggleRecording('${model.name}', false)">Stop</button>` : ''}
                        </div>
                    </div>`
                ).join('');
            }
        }
        
        async function loadRecordings() {
            const model = document.getElementById('recording-filter').value;
            const recordings = await apiCall('get_recordings', { model });
            if (!recordings.error) {
                document.getElementById('recordings-list').innerHTML = recordings.map(rec => 
                    `<div class="recording-item">
                        <div class="recording-info">
                            <h4>${rec.model} - ${rec.duration}</h4>
                            <p>${rec.file_path} • ${rec.file_size} • ${rec.created_at}</p>
                        </div>
                        <div>
                            ${rec.file_path.endsWith('.mp4') ? 
                                `<video class="video-player" controls><source src="/local${rec.file_path}" type="video/mp4"></video>` : 
                                `<button class="btn" onclick="convertRecording('${rec.file_path}')">Convert to MP4</button>`
                            }
                        </div>
                    </div>`
                ).join('');
            }
        }
        
        async function loadLocations() {
            const locations = await apiCall('get_locations');
            if (!locations.error) {
                document.getElementById('locations-list').innerHTML = locations.map(loc => 
                    `<div class="status-item">
                        <div>
                            <strong>${loc.name}</strong><br>
                            <small>${loc.path}</small><br>
                            <small>${loc.description}</small>
                        </div>
                        <div>
                            ${loc.custom ? `<button class="btn danger" onclick="removeLocation('${loc.id}')">Remove</button>` : ''}
                        </div>
                    </div>`
                ).join('');
            }
        }
        
        async function loadLogs() {
            const level = document.getElementById('log-level').value;
            const logs = await apiCall('get_logs', { level });
            if (!logs.error) {
                document.getElementById('logs-container').innerHTML = logs.map(log => 
                    `<div class="log-entry ${log.level.toLowerCase()}">
                        <strong>${log.timestamp}</strong> ${log.message}
                    </div>`
                ).join('');
            }
        }
        
        async function addLocation() {
            const name = document.getElementById('location-name').value;
            const path = document.getElementById('location-path').value;
            
            if (!name || !path) {
                alert('Please enter both name and path');
                return;
            }
            
            const result = await apiCall('add_location', { name, path });
            if (!result.error) {
                document.getElementById('location-name').value = '';
                document.getElementById('location-path').value = '';
                loadLocations();
            } else {
                alert('Error: ' + result.error);
            }
        }
        
        async function removeLocation(locationId) {
            if (confirm('Remove this location?')) {
                const result = await apiCall('remove_location', { location_id: locationId });
                if (!result.error) {
                    loadLocations();
                } else {
                    alert('Error: ' + result.error);
                }
            }
        }
        
        async function toggleRecording(model, start) {
            const action = start ? 'start_recording' : 'stop_recording';
            const result = await apiCall(action, { model });
            if (!result.error) {
                loadModels();
            } else {
                alert('Error: ' + result.error);
            }
        }
        
        // Auto-refresh dashboard every 30 seconds
        setInterval(() => {
            if (document.getElementById('dashboard').classList.contains('active')) {
                loadDashboard();
            }
        }, 30000);
        
        // Initial load
        loadDashboard();
    </script>
</body>
</html>
        """
        return self.hass.http.response_factory.html(html)
    
    async def _get_status(self) -> Dict[str, Any]:
        """Get system status."""
        try:
            data = {}
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                coordinator = entry_data.get("coordinator")
                file_manager = entry_data.get("file_manager")
                
                items = []
                stats = {
                    "total_recordings": 0,
                    "active_recordings": 0,
                    "storage_used_gb": 0
                }
                
                if coordinator and coordinator.data:
                    for model, state in coordinator.data.items():
                        items.append({
                            "name": model,
                            "online": state.status == "public",
                            "title": state.title,
                            "viewer_count": state.viewer_count
                        })
                
                if file_manager:
                    file_stats = file_manager.get_stats()
                    stats.update(file_stats)
                
                data[entry_id] = {"items": items, "stats": stats}
            
            return data
        except Exception as exc:
            _LOGGER.error("Error getting status: %s", exc)
            return {"error": str(exc)}
    
    async def _get_models(self) -> List[Dict[str, Any]]:
        """Get model information."""
        try:
            models = []
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                coordinator = entry_data.get("coordinator")
                if coordinator and coordinator.data:
                    for model, state in coordinator.data.items():
                        models.append({
                            "name": model,
                            "online": state.status == "public",
                            "title": state.title,
                            "viewer_count": state.viewer_count,
                            "recording": False  # TODO: Check recording status
                        })
            return models
        except Exception as exc:
            _LOGGER.error("Error getting models: %s", exc)
            return [{"error": str(exc)}]
    
    async def _get_recordings(self, model: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recording information."""
        try:
            recordings = []
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                file_manager = entry_data.get("file_manager")
                if file_manager:
                    # TODO: Implement recording listing
                    pass
            return recordings
        except Exception as exc:
            _LOGGER.error("Error getting recordings: %s", exc)
            return [{"error": str(exc)}]
    
    async def _get_locations(self) -> List[Dict[str, Any]]:
        """Get available locations."""
        try:
            locations = []
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                location_manager = entry_data.get("location_manager")
                if location_manager:
                    available = await location_manager.async_get_available_locations()
                    for loc in available:
                        locations.append({
                            "id": loc["path"],
                            "name": loc["name"],
                            "path": loc["path"],
                            "description": loc["description"],
                            "custom": loc["path"].startswith("/config") or not loc["path"].startswith("/")
                        })
            return locations
        except Exception as exc:
            _LOGGER.error("Error getting locations: %s", exc)
            return [{"error": str(exc)}]
    
    async def _add_location(self, name: str, path: str) -> Dict[str, Any]:
        """Add a custom location."""
        try:
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                location_manager = entry_data.get("location_manager")
                if location_manager:
                    success, message = await location_manager.async_add_custom_location(name, path)
                    return {"success": success, "message": message}
            return {"error": "Location manager not available"}
        except Exception as exc:
            _LOGGER.error("Error adding location: %s", exc)
            return {"error": str(exc)}
    
    async def _remove_location(self, location_id: str) -> Dict[str, Any]:
        """Remove a custom location."""
        try:
            for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
                location_manager = entry_data.get("location_manager")
                if location_manager:
                    success, message = await location_manager.async_remove_location(location_id)
                    return {"success": success, "message": message}
            return {"error": "Location manager not available"}
        except Exception as exc:
            _LOGGER.error("Error removing location: %s", exc)
            return {"error": str(exc)}
    
    async def _get_logs(self, level: str = "INFO") -> List[Dict[str, Any]]:
        """Get system logs."""
        try:
            # TODO: Implement log retrieval
            return [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": level,
                    "message": "Log retrieval not yet implemented"
                }
            ]
        except Exception as exc:
            _LOGGER.error("Error getting logs: %s", exc)
            return [{"error": str(exc)}]