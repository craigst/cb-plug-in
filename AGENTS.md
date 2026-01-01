# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-01 22:36:14
**Commit:** 70038f3
**Branch:** main

## OVERVIEW
Home Assistant custom integration for Chaturbate Bridge, built with Python asyncio. Polls Chaturbate API, manages streams via go2rtc, and handles recording with NAS transfer.

## STRUCTURE
```
./
├── custom_components/chaturbate_bridge/    # Integration core files
├── RELEASE_NOTES_v7.7.0.md
├── RELEASE_NOTES_v7.7.1.md
├── RELEASE_PROCESS.md
├── STORAGE_MANAGEMENT.md
└── hacs.json
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add new entity | custom_components/chaturbate_bridge/ | Add platform file (sensor.py, binary_sensor.py) |
| Modify API polling | coordinator.py | Update _async_update_data or _fetch_variants |
| Change config schema | config_flow.py | Add validation in async_step_user |
| Fix recording logic | switch.py | Update async_update for recorder state |
| Handle storage | file_manager.py | Modify _run loop for NAS transfers |

## CODE MAP
No LSP available - see explore analysis for hotspots.

## CONVENTIONS
- Blind exception handling allowed with `# noqa: BLE001` for API robustness
- Blocking I/O wrapped in `hass.async_add_executor_job`
- Dynamic entity creation/removal via coordinator listeners

## ANTI-PATTERNS (THIS PROJECT)
- Blocking I/O in async functions (use executor)
- Broad exception catching without noqa
- Invalid empty paths (convert to None)
- Direct file ops in async loop (background only)

## UNIQUE STYLES
- Hybrid state: ModelState dataclasses + Store persistence
- Process management: asyncio subprocess for ffmpeg
- NAS validation: touch/unlink test file for availability

## COMMANDS
No automated dev/test/build. Manual release process documented in RELEASE_PROCESS.md.

## NOTES
- Version sync required in manifest.json and const.py
- No automated tests; manual validation on test instances
- go2rtc integration uses REST API for stream management</content>
<parameter name="filePath">./AGENTS.md