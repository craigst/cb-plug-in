
from __future__ import annotations
import re
from urllib.parse import urlparse
import voluptuous as vol
from homeassistant import config_entries
from .const import (
    DEFAULT_EXPOSE_VARIANTS,
    DEFAULT_GO2RTC_URL,
    DEFAULT_MODE,
    DEFAULT_PUBLIC_GO2RTC_BASE,
    DEFAULT_RECORD_BASE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_LOCAL_RECORD_PATH,
    DEFAULT_REMOTE_RECORD_PATH,
    DEFAULT_ENABLE_AUTO_MOVE,
    DEFAULT_NAS_CHECK_INTERVAL,
    DEFAULT_AUTO_CLEANUP,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_MIN_FREE_SPACE_GB,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MODEL_PLACEHOLDER,
)

_MODEL_RE = re.compile(r"^[A-Za-z0-9_]+$")

STEP_USER = vol.Schema({
    vol.Required("go2rtc_url", default=DEFAULT_GO2RTC_URL): str,
    vol.Required("record_base", default=DEFAULT_RECORD_BASE): str,
    vol.Required("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
    vol.Required("mode", default=DEFAULT_MODE): vol.In(["plain", "ffmpeg"]),
    vol.Required(
        "models",
        default="",
        description={"suggested_value": MODEL_PLACEHOLDER},
    ): str,
    vol.Optional("public_go2rtc_base", default=DEFAULT_PUBLIC_GO2RTC_BASE): str,
    vol.Required("expose_variants", default=DEFAULT_EXPOSE_VARIANTS): bool,
})

STEP_OPTIONS = vol.Schema({
    vol.Required(
        "models",
        default="",
        description={"suggested_value": MODEL_PLACEHOLDER},
    ): str,
    vol.Required("record_base", default=DEFAULT_RECORD_BASE): str,
    vol.Required("expose_variants", default=DEFAULT_EXPOSE_VARIANTS): bool,
    vol.Optional("local_record_path", default=DEFAULT_LOCAL_RECORD_PATH): str,
    vol.Optional("remote_record_path", default=DEFAULT_REMOTE_RECORD_PATH): str,
    vol.Optional("enable_auto_move", default=DEFAULT_ENABLE_AUTO_MOVE): bool,
    vol.Optional("nas_check_interval", default=DEFAULT_NAS_CHECK_INTERVAL): vol.All(int, vol.Range(min=30, max=600)),
    vol.Optional("auto_cleanup", default=DEFAULT_AUTO_CLEANUP): bool,
    vol.Optional("retention_days", default=DEFAULT_RETENTION_DAYS): vol.All(int, vol.Range(min=1, max=365)),
    vol.Optional("min_free_space_gb", default=DEFAULT_MIN_FREE_SPACE_GB): vol.All(int, vol.Range(min=1, max=1000)),
})

def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _is_valid_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _parse_models(raw: str) -> list[str]:
    models = [m.strip() for m in raw.split(",") if m.strip()]
    for model in models:
        if not _MODEL_RE.fullmatch(model):
            raise ValueError(model)
    return models


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER)
        errors: dict[str, str] = {}
        go2rtc_url = user_input["go2rtc_url"].strip()
        if not _is_valid_url(go2rtc_url):
            errors["go2rtc_url"] = "invalid_url"
        models: list[str] = []
        try:
            models = _parse_models(user_input.get("models", ""))
        except ValueError:
            errors["models"] = "invalid_models"
        scan_interval = int(user_input["scan_interval"])
        if scan_interval < MIN_SCAN_INTERVAL or scan_interval > MAX_SCAN_INTERVAL:
            errors["scan_interval"] = "invalid_scan_interval"
        public_base_raw = user_input.get("public_go2rtc_base", "").strip()
        if public_base_raw and not _is_valid_url(public_base_raw):
            errors["public_go2rtc_base"] = "invalid_url"
        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER,
                errors=errors,
                user_input=user_input,
            )
        record_base = user_input.get("record_base", DEFAULT_RECORD_BASE)
        record_base = record_base.strip() if isinstance(record_base, str) else DEFAULT_RECORD_BASE
        data = {
            "go2rtc_url": _normalize_url(go2rtc_url),
            "scan_interval": scan_interval,
            "mode": user_input["mode"],
            "record_base": record_base or DEFAULT_RECORD_BASE,
            "models": models,
            "public_go2rtc_base": _normalize_url(public_base_raw or go2rtc_url or DEFAULT_PUBLIC_GO2RTC_BASE),
            "expose_variants": bool(user_input["expose_variants"]),
        }
        return self.async_create_entry(title="Chaturbate Bridge", data=data)

    async def async_step_import(self, user_input):
        return await self.async_step_user(user_input)

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            errors: dict[str, str] = {}
            try:
                models = _parse_models(user_input.get("models", ""))
            except ValueError:
                errors["models"] = "invalid_models"
            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=STEP_OPTIONS,
                    errors=errors,
                )
            record_base = user_input.get("record_base", DEFAULT_RECORD_BASE)
            record_base = record_base.strip() if isinstance(record_base, str) else DEFAULT_RECORD_BASE
            
            local_path = user_input.get("local_record_path", DEFAULT_LOCAL_RECORD_PATH)
            remote_path = user_input.get("remote_record_path", DEFAULT_REMOTE_RECORD_PATH)
            
            return self.async_create_entry(title="", data={
                "models": models,
                "record_base": record_base or DEFAULT_RECORD_BASE,
                "expose_variants": bool(user_input.get("expose_variants", DEFAULT_EXPOSE_VARIANTS)),
                "local_record_path": local_path.strip() if isinstance(local_path, str) else DEFAULT_LOCAL_RECORD_PATH,
                "remote_record_path": remote_path.strip() if isinstance(remote_path, str) else DEFAULT_REMOTE_RECORD_PATH,
                "enable_auto_move": bool(user_input.get("enable_auto_move", DEFAULT_ENABLE_AUTO_MOVE)),
                "nas_check_interval": int(user_input.get("nas_check_interval", DEFAULT_NAS_CHECK_INTERVAL)),
                "auto_cleanup": bool(user_input.get("auto_cleanup", DEFAULT_AUTO_CLEANUP)),
                "retention_days": int(user_input.get("retention_days", DEFAULT_RETENTION_DAYS)),
                "min_free_space_gb": int(user_input.get("min_free_space_gb", DEFAULT_MIN_FREE_SPACE_GB)),
            })
        
        current = self.config_entry.options.get("models", self.config_entry.data.get("models", []))
        expose = self.config_entry.options.get("expose_variants", self.config_entry.data.get("expose_variants", DEFAULT_EXPOSE_VARIANTS))
        local_path = self.config_entry.options.get("local_record_path", self.config_entry.data.get("local_record_path", DEFAULT_LOCAL_RECORD_PATH))
        remote_path = self.config_entry.options.get("remote_record_path", self.config_entry.data.get("remote_record_path", DEFAULT_REMOTE_RECORD_PATH))
        enable_auto_move = self.config_entry.options.get("enable_auto_move", self.config_entry.data.get("enable_auto_move", DEFAULT_ENABLE_AUTO_MOVE))
        nas_check_interval = self.config_entry.options.get("nas_check_interval", self.config_entry.data.get("nas_check_interval", DEFAULT_NAS_CHECK_INTERVAL))
        auto_cleanup = self.config_entry.options.get("auto_cleanup", self.config_entry.data.get("auto_cleanup", DEFAULT_AUTO_CLEANUP))
        retention_days = self.config_entry.options.get("retention_days", self.config_entry.data.get("retention_days", DEFAULT_RETENTION_DAYS))
        min_free_space = self.config_entry.options.get("min_free_space_gb", self.config_entry.data.get("min_free_space_gb", DEFAULT_MIN_FREE_SPACE_GB))
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("models", default=", ".join(current)): str,
                vol.Required("record_base", default=self.config_entry.options.get("record_base", self.config_entry.data.get("record_base", DEFAULT_RECORD_BASE))): str,
                vol.Required("expose_variants", default=expose): bool,
                vol.Optional("local_record_path", default=local_path): str,
                vol.Optional("remote_record_path", default=remote_path): str,
                vol.Optional("enable_auto_move", default=enable_auto_move): bool,
                vol.Optional("nas_check_interval", default=nas_check_interval): vol.All(int, vol.Range(min=30, max=600)),
                vol.Optional("auto_cleanup", default=auto_cleanup): bool,
                vol.Optional("retention_days", default=retention_days): vol.All(int, vol.Range(min=1, max=365)),
                vol.Optional("min_free_space_gb", default=min_free_space): vol.All(int, vol.Range(min=1, max=1000)),
            })
        )
