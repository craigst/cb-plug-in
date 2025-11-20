# v7.7.1 - Bug Fixes

## Bug Fixes

### Critical Fixes
- **Fixed empty string remote path handling** - Empty remote path now properly defaults to None instead of creating invalid Path("")
- **Fixed blocking I/O in async function** - Directory creation now properly uses executor to avoid blocking async event loop
- **Improved path validation** - Better handling of whitespace in path configurations

### Technical Details

**File Manager Improvements:**
- Remote path validation now strips whitespace and converts empty strings to None
- Async directory creation uses executor to prevent blocking
- More robust error handling for path operations

**Backward Compatibility:**
- All fixes are backward compatible with v7.7.0
- Existing configurations continue to work without changes
- State persistence remains unchanged

## What's Still Included from v7.7.0

All features from v7.7.0 remain:
- ✅ Recording settings persistence
- ✅ Stream start/finish tracking
- ✅ Dual storage (local + NAS)
- ✅ Auto-transfer to NAS
- ✅ Offline resilience
- ✅ Storage monitoring
- ✅ Auto cleanup
- ✅ Custom record icon

## Upgrade Instructions

### From v7.7.0
Simply update via HACS - no configuration changes needed.

### From Earlier Versions
1. Update via HACS
2. Restart Home Assistant
3. Configure storage options in integration settings (optional)

## Files Changed from v7.7.0
- `file_manager.py` - Path handling and async fixes
- `const.py` - Version bump to 7.7.1
- `manifest.json` - Version bump to 7.7.1
