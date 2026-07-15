from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_role_key: str
    request_timeout: int = 25
    manual_base_rate: float | None = None
    manual_tonia_rate: float | None = None
    template_path: Path = ROOT_DIR / "templates" / "macro_template.pptx"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def load_settings(overrides: Mapping[str, object] | None = None) -> Settings:
    values: dict[str, object] = dict(os.environ)
    local_secrets = ROOT_DIR / ".streamlit" / "secrets.toml"
    if local_secrets.exists():
        with local_secrets.open("rb") as file:
            values.update(tomllib.load(file))
    if overrides:
        values.update(overrides)

    return Settings(
        supabase_url=str(values.get("SUPABASE_URL", "")).strip(),
        supabase_service_role_key=str(
            values.get("SUPABASE_SERVICE_ROLE_KEY", "")
        ).strip(),
        request_timeout=int(values.get("REQUEST_TIMEOUT", 25)),
        manual_base_rate=_optional_float(values.get("MANUAL_BASE_RATE")),
        manual_tonia_rate=_optional_float(values.get("MANUAL_TONIA_RATE")),
    )
