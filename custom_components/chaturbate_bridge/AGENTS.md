# CHATURBATE BRIDGE CORE

**Generated:** 2026-01-01 22:48:00

## OVERVIEW
Asyncio-driven integration core for polling Chaturbate room states, pushing HLS streams to go2rtc, and managing local MKV recordings with background NAS synchronization.

## WHERE TO LOOK
| Component | Responsibility | Key Logic |
|-----------|----------------|-----------|
| `coordinator.py` | HLS & go2rtc | `_fetch_variants` (parsing), `_upsert_go2rtc` (REST calls), `ModelState` dataclass |
| `file_manager.py` | Storage Ops | `_pending_moves` queue, `_check_disk_space`, NAS heartbeat, retention cleanup |
| `recorder.py` | FFmpeg Wrapper | `asyncio.subprocess` lifecycle, `.mkv` path generation using `datetime` |
| `switch.py` | Recording | `async_turn_on/off` coordination with `FFmpegRecorder` and `FileManager` |
| `camera.py` | Dynamic Entities | Mapping `ModelState` variants to dynamic camera entities with resolution suffixes |
| `sensor.py` | Metadata | Exposing `viewer_count`, `title`, and online variants via HA sensors |
| `binary_sensor.py` | Presence | Binary online/offline status tracking with custom icons |
| `const.py` | Config Defaults | Default storage paths (`/config/media/...`), API endpoints, and timeouts |

## STATE FLOW
1. **Poll**: `ChaturbateCoordinator` hits `CB_EDGE_URL` to get the master HLS URL.
2. **Resolve**: `_fetch_variants` parses the master playlist to extract all resolution/bandwidth pairs.
3. **Register**: `_upsert_go2rtc` pushes stream definitions to the go2rtc REST API.
4. **Notify**: Entities update via `DataUpdateCoordinator` listeners; dynamic cameras are added/removed.
5. **Record**: If a switch is active, `FFmpegRecorder` starts an async subprocess to capture the stream.
6. **Move**: Upon recording completion, `FileManager` queues the file for NAS transfer if online.

## CONVENTIONS
- **HLS Orchestration**: Always sort variants by bandwidth; the highest-rated variant is aliased to the model's base name in go2rtc for the primary camera.
- **Transfer Reliability**: `FileManager` uses a retry loop (max 5 attempts) for NAS transfers, persisting the queue via Home Assistant `Store` to `.storage/chaturbate_bridge.file_manager`.
- **Stream Relay**: Mode `ffmpeg` adds specific input headers (`Referer`, `User-Agent`) to the go2rtc source string to bypass Chaturbate's hotlink protection.
- **Cleanup Policy**: Automatic deletion of `.mkv` files older than `retention_days` runs hourly within the `FileManager._run()` background loop.
- **Async Execution**: All potentially blocking operations (filesystem, NAS checks) must be wrapped in `hass.async_add_executor_job`.

## ANTI-PATTERNS
- **Main-loop File Ops**: Never use `shutil.move` or `Path.mkdir` directly in async methods; delegate to the executor.
- **Unchecked Transfers**: Do not remove items from `_pending_moves` until `shutil.move` is confirmed successful or max retries are reached.
- **Hardcoded Media Paths**: Use `DEFAULT_LOCAL_RECORD_PATH` or resolved config-relative paths to ensure the integration works across different HA OS installations.
- **Sync Subprocesses**: Avoid `subprocess.run` or `os.system`; use `FFmpegRecorder` which utilizes `asyncio.create_subprocess_exec` for non-blocking execution.
- **Broad Exceptions**: Avoid catching `Exception` without the `# noqa: BLE001` marker in API-facing code to maintain linter compliance while ensuring robustness.
