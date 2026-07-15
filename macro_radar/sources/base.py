from __future__ import annotations

from typing import Protocol

from macro_radar.models import Observation


class Connector(Protocol):
    name: str

    def fetch(self) -> list[Observation]: ...
