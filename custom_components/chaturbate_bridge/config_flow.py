
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
                    data_schema=STEP_OPTIONS.extend({
                        vol.Required("models", default=user_input.get("models", "")): str,
                        vol.Required("expose_variants", default=bool(user_input.get("expose_variants", True))): bool,
                    }),
                    errors=errors,
                )
            record_base = user_input.get("record_base", DEFAULT_RECORD_BASE)
            record_base = record_base.strip() if isinstance(record_base, str) else DEFAULT_RECORD_BASE
            return self.async_create_entry(title="", data={
                "models": models,
                "record_base": record_base or DEFAULT_RECORD_BASE,
                "expose_variants": bool(user_input["expose_variants"]),
            })
        current = self.config_entry.options.get("models", self.config_entry.data.get("models", []))
        expose = self.config_entry.options.get("expose_variants", self.config_entry.data.get("expose_variants", True))
        return self.async_show_form(
            step_id="init",
            data_schema=STEP_OPTIONS.extend({
                vol.Required("models", default=", ".join(current)): str,
                vol.Required("expose_variants", default=expose): bool,
            })
        )
