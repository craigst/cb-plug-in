
# Chaturbate Bridge (v7.6.0)

Stream public Chaturbate rooms directly into Home Assistant using go2rtc. The integration watches your favourite models, auto-manages go2rtc stream aliases (including per-resolution variants), surfaces sensors for online state and viewer counts, and exposes optional one-click recording switches.

## Features
- Dynamic camera entities (best stream + resolution variants) that appear/disappear with room status
- Binary sensor, sensor, and switch entities for each configured model
- Automatic go2rtc stream management using either native or ffmpeg relay modes
- Optional per-model MKV recording with auto-stop when a room goes offline
- Strict input validation, robust error handling, and informative logging to simplify troubleshooting

## Requirements
- Home Assistant 2023.6 or newer
- go2rtc instance reachable from Home Assistant (default: `http://127.0.0.1:1984`)
- Custom component installed under `config/custom_components/chaturbate_bridge/`

## Installation

### via HACS
1. Add your GitHub repository (`https://github.com/YOUR_USERNAME/chaturbate-bridge`) to HACS as a custom integration.
2. Search for **Chaturbate Bridge** inside HACS → Integrations and install it.
3. Restart Home Assistant.

### Manual Install
1. Download or clone the repository.
2. Copy the `chaturbate_bridge` folder to `config/custom_components/chaturbate_bridge/`.
3. Restart Home Assistant.

## Configuration

1. Navigate to **Settings → Integrations → Add Integration**.
2. Search for **Chaturbate Bridge**.
3. Supply the required fields:
   - **go2rtc URL**: Base URL to your go2rtc server (supports HTTP/HTTPS).
   - **Record base**: `media` by default. Relative paths are resolved within `/config`, absolute paths are honoured.
   - **Scan interval (s)**: Polling frequency (allowed range 5–300 seconds).
   - **Mode**: `plain` (direct go2rtc pull) or `ffmpeg` (relay via ffmpeg).
   - **Models**: Comma-separated model list, e.g. `model1, model2`.
   - **Public go2rtc base**: Optional public URL/base if different from the internal go2rtc URL.
   - **Expose variants**: When enabled, per-resolution camera entities are created alongside the primary stream.

### Options Flow
- Update model list, recording base, and variant exposure after the initial setup via **Configure** on the integration card.
- Model names are validated (letters, numbers, and underscores only). Invalid names surface a form error.

## Entity Overview
- **Camera**: `camera.cb_<model>` plus variant cameras when available.
- **Binary Sensor**: Online/offline status per model.
- **Sensor**: Rich status including viewer count, title, and available variants.
- **Switch**: Optional recording control that writes MKV segments into `<record_base>/<model>/`.

## Screenshots
> _Replace with your own screenshots once the repository is public._
- Home Assistant dashboard card showing live stream (insert image path here).
- Integration configuration form (insert image path here).

## Troubleshooting
- **Validation errors**: Check form hints; URLs must include `http://` or `https://` and model names must be alphanumeric/underscore.
- **go2rtc connectivity**: Review Home Assistant logs for `chaturbate_bridge` entries. HTTP errors return the response body to speed up debugging.
- **Snapshots missing**: Ensure go2rtc exposes `/api/frame.jpeg` and Home Assistant can reach the public base URL.
- **Recorder not writing files**: Confirm Home Assistant has write permissions to the configured `record_base`.

## Contributing
- Fork the repository, create a feature branch, and open a pull request.
- Please include linting/formatting updates and describe validation steps in the PR.

## License
Released under the MIT License. See [LICENSE](../../LICENSE) for details.
