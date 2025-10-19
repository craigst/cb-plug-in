"""Constants for the Chaturbate Bridge integration."""

DOMAIN = "chaturbate_bridge"
INTEGRATION_VERSION = "7.6.0"

DEFAULT_GO2RTC_URL = "http://127.0.0.1:1984"
DEFAULT_PUBLIC_GO2RTC_BASE = DEFAULT_GO2RTC_URL
DEFAULT_RECORD_BASE = "media"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_MODE = "plain"
DEFAULT_EXPOSE_VARIANTS = True

DEFAULT_TIMEOUT = 30  # seconds

MODEL_PLACEHOLDER = "model1, model2"
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300

USER_AGENT = "HA-CB-Bridge/1.0"
CB_EDGE_URL = "https://chaturbate.com/get_edge_hls_url_ajax/"
GO2RTC_STREAM_ENDPOINT = "/api/streams"
INTEGRATION_TITLE = "Chaturbate Bridge"
