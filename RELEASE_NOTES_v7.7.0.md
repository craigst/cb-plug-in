# v7.7.0 - Storage Management System

## New Features

### Storage Management System
- **Dual Storage**: Local recording with optional NAS transfer
- **Auto-Transfer**: Files automatically move to NAS when it comes online
- **Offline Resilience**: Continues recording locally when NAS is unavailable
- **Smart Retry**: Failed transfers retry up to 5 times
- **Auto Cleanup**: Optional old file deletion with configurable retention
- **Storage Monitoring**: New sensor tracks NAS status, transfers, and statistics

### Improvements
- **Recording Settings Persistence**: Switches remember their state across restarts
- **Stream Tracking**: Stream start/end times and duration are now persisted
- **Custom Icon**: Added record button icon

### Configuration
New options in integration settings:
- Local Record Path
- Remote Record Path (optional)
- Enable Auto Move
- NAS Check Interval (30-600s)
- Auto Cleanup
- Retention Days (1-365)
- Min Free Space (1-1000 GB)

### NAS Support
NAS is completely optional - the system works standalone with just local storage. Leave Remote Record Path empty to disable NAS features.

See `STORAGE_MANAGEMENT.md` for detailed documentation and examples.

## Installation

### New Installation
1. Add this repository to HACS
2. Download "Chaturbate Bridge"
3. Restart Home Assistant
4. Add integration via Settings → Integrations

### Upgrade from Previous Version
1. Update via HACS
2. Restart Home Assistant
3. Configure storage options in integration settings
4. Turn recording switches back on (they reset to off after upgrade)

## Files Changed
- Added: `file_manager.py`, `storage_sensor.py`, `icon.png`, `STORAGE_MANAGEMENT.md`
- Modified: `switch.py`, `__init__.py`, `config_flow.py`, `const.py`, `manifest.json`, `hacs.json`
