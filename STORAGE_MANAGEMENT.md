# Storage Management System

This document describes the new storage management features added to the Chaturbate Bridge integration in version 7.7.0.

## Overview

The storage management system allows you to:
- Record streams locally when your NAS is offline
- Automatically move recordings to your NAS when it comes online
- Monitor NAS availability in real-time
- Track pending file transfers
- Automatically clean up old recordings
- Monitor storage statistics

## Configuration

Access the integration's options in Home Assistant to configure storage settings:

### Storage Paths

- **Local Record Path** (default: `/config/media/chaturbate/local`)
  - Where recordings are initially saved
  - Should be on your Home Assistant instance's local storage
  - Recordings stay here until moved to NAS

- **Remote Record Path** (default: empty)
  - Your NAS mount point (e.g., `/media/nas/recordings`)
  - Leave empty to disable NAS transfers
  - Must be a mounted network drive or SMB/NFS share

### Transfer Settings

- **Enable Auto Move** (default: enabled)
  - Automatically transfer completed recordings to NAS when available
  - Files remain in queue until successfully transferred
  - Retries failed transfers up to 5 times

- **NAS Check Interval** (30-600 seconds, default: 60)
  - How often to check if NAS is online
  - Lower values = faster detection but more system load
  - Higher values = less system load but slower detection

### Cleanup Settings

- **Auto Cleanup** (default: disabled)
  - Automatically delete old recordings based on retention policy
  - Applies to both local and remote storage

- **Retention Days** (1-365 days, default: 30)
  - How long to keep recordings before deletion
  - Only applies when Auto Cleanup is enabled

- **Minimum Free Space** (1-1000 GB, default: 10)
  - Minimum free space to maintain on local storage
  - Triggers warnings in logs when threshold is reached

## How It Works

### Recording Workflow

1. **Stream starts** → Recording begins in local path
2. **Stream ends** → Recording file is finalized
3. **File queued** → Completed recording is queued for NAS transfer
4. **NAS check** → System checks if NAS is mounted and writable
5. **Transfer** → If NAS is online, file is moved to remote path
6. **Retry** → If transfer fails, it's retried on next check (up to 5 attempts)

### NAS Detection

The system checks NAS availability by:
1. Verifying the remote path exists
2. Creating a test file (`.chaturbate_bridge_test`)
3. Deleting the test file
4. If all steps succeed, NAS is considered online

### Monitoring

#### Recording Switch Attributes

Each recording switch now includes:
- `nas_online`: Current NAS status (true/false)
- `pending_transfers`: Number of files waiting to be moved
- `last_live_start`: When the last stream started
- `last_live_end`: When the last stream ended
- `last_stream_duration_sec`: Duration in seconds
- `last_stream_duration_hr`: Human-readable duration

#### Storage Manager Sensor

A new sensor `sensor.chaturbate_storage_manager` provides:
- **State**: `online` or `offline` (NAS status)
- **Attributes**:
  - `nas_status`: Current NAS availability
  - `pending_files`: Files waiting for transfer
  - `total_moved`: Total files successfully transferred
  - `total_moved_gb`: Total data transferred in GB
  - `failed_moves`: Number of failed transfer attempts
  - `last_move_time`: Timestamp of last successful transfer
  - `local_path`: Configured local storage path
  - `remote_path`: Configured NAS path
  - `auto_move_enabled`: Whether auto-move is enabled

## Example Setup

### Mounting NAS in Home Assistant

If using Home Assistant OS/Supervised, mount your NAS using the Samba or NFS add-on.

For Docker installations, mount NAS in your docker-compose:
```yaml
volumes:
  - /path/to/nas:/media/nas:rw
```

### Configuration Example

1. Go to **Settings** → **Devices & Services**
2. Find **Chaturbate Bridge** and click **Configure**
3. Set paths:
   - Local: `/config/media/chaturbate/local`
   - Remote: `/media/nas/recordings`
4. Enable **Auto Move**
5. Set **NAS Check Interval** to 60 seconds
6. Enable **Auto Cleanup** if desired
7. Set **Retention Days** to your preference

### Automation Examples

#### Notify when NAS comes online
```yaml
automation:
  - alias: "NAS Online Notification"
    trigger:
      - platform: state
        entity_id: sensor.chaturbate_storage_manager
        to: "online"
    action:
      - service: notify.mobile_app
        data:
          message: "NAS is now online. File transfers will begin."
```

#### Alert on pending transfers
```yaml
automation:
  - alias: "Pending Transfers Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.chaturbate_storage_manager
        attribute: pending_files
        above: 10
    action:
      - service: notify.mobile_app
        data:
          message: "{{ state_attr('sensor.chaturbate_storage_manager', 'pending_files') }} recordings waiting for NAS transfer"
```

#### Daily storage report
```yaml
automation:
  - alias: "Daily Storage Report"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: notify.mobile_app
        data:
          message: >
            Storage Report:
            - NAS: {{ states('sensor.chaturbate_storage_manager') }}
            - Pending: {{ state_attr('sensor.chaturbate_storage_manager', 'pending_files') }} files
            - Transferred: {{ state_attr('sensor.chaturbate_storage_manager', 'total_moved_gb') }} GB
```

## Troubleshooting

### Files not transferring

1. Check NAS is mounted: `ls -la /media/nas`
2. Verify permissions: User running HA needs write access
3. Check logs: Look for "Failed to move file" errors
4. Verify `sensor.chaturbate_storage_manager` shows `online`

### NAS shows offline but is mounted

1. Check remote path is correct in configuration
2. Ensure Home Assistant has write permissions
3. Try creating a file manually in the remote path
4. Check network connectivity to NAS

### Local storage filling up

1. Enable **Auto Cleanup** to remove old files
2. Lower **Retention Days** value
3. Increase **NAS Check Interval** if transfers are slow
4. Manually clear local storage: remove old files from local path

### Recordings lost after restart

Recordings are never lost! The system persists:
- Armed state of recording switches
- Stream start/end times
- Pending file transfers

All data is restored when Home Assistant restarts.

## Storage Locations

The integration stores data in these locations:

- **Recordings**: 
  - Local: `<local_record_path>/<model>/`
  - Remote: `<remote_record_path>/<model>/`
- **State persistence**: 
  - `.storage/chaturbate_bridge.switch_states`
  - `.storage/chaturbate_bridge.file_manager`

## Performance Considerations

- **NAS Check Interval**: Lower values increase responsiveness but add system load
- **Auto Cleanup**: Runs once per hour, minimal impact
- **File Transfers**: Run in background, don't block recording
- **Large Files**: Transfers may take time; system handles this gracefully

## Upgrade Notes

When upgrading from previous versions:
1. Recording switches will default to OFF (unarmed)
2. Turn them ON again to resume auto-recording
3. Configure storage paths in integration options
4. Old recordings in `record_base` path remain untouched
5. New recordings use the storage management system
