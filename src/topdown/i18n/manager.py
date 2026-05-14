from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class I18NManager:
    """Simple key-value localization provider."""

    root_dir: Path
    current_language: str

    def translate(self, key: str) -> str:
        """Return a localized string or the key itself when missing.

        Args:
            key: Localization key.

        Returns:
            Localized text.
        """
        language_file = self.root_dir / self.current_language / "ui.lang"
        if not language_file.exists():
            return key

        with language_file.open("r", encoding="utf-8") as file_obj:
            for line in file_obj:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                current_key, value = stripped.split("=", 1)
                if current_key == key:
                    return value
        return key
