from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Theme:
    name: str
    colors: dict[str, str]
    icons_enabled: bool


class ThemeManager:
    _current_theme: Optional[Theme] = None

    @classmethod
    def load(cls, config_path: Path) -> None: ...

    @classmethod
    def get_color(cls, key: str) -> str: ...

    @classmethod
    def style(cls, text: str, color_key: str) -> str: ...
