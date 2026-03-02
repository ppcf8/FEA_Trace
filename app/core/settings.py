"""
app/core/settings.py — User preference persistence (project-code & entity-name presets).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_SETTINGS_DIR  = Path.home() / "Documents" / "FEA_Trace"
_SETTINGS_PATH = _SETTINGS_DIR / "settings.json"


@dataclass
class AppSettings:
    project_presets: dict[str, list[str]] = field(default_factory=dict)
    # {"PROJ_A": ["Wing", "Fuselage"], "PROJ_B": ["Door", "Bracket"]}


class SettingsManager:
    def __init__(self) -> None:
        self.settings = AppSettings()
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _SETTINGS_PATH.exists():
            return
        try:
            raw = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            presets = raw.get("project_presets", {})
            if isinstance(presets, dict):
                self.settings.project_presets = {
                    str(k): [str(n) for n in v] if isinstance(v, list) else []
                    for k, v in presets.items()
                }
        except Exception:
            # Silently ignore corrupt / unreadable settings
            pass

    def save(self) -> None:
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        _SETTINGS_PATH.write_text(
            json.dumps(
                {"project_presets": self.settings.project_presets},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def project_codes(self) -> list[str]:
        """Sorted list of all preset project codes."""
        return sorted(self.settings.project_presets.keys())

    def entity_names_for(self, project_code: str) -> list[str]:
        """Names for the given code.

        If the code is not in the presets, return the union of all names
        across all codes (fallback for free-typed codes).
        """
        presets = self.settings.project_presets
        if project_code in presets:
            return list(presets[project_code])
        # Fallback: union of all names, preserving insertion order
        seen: set[str] = set()
        result: list[str] = []
        for names in presets.values():
            for n in names:
                if n not in seen:
                    seen.add(n)
                    result.append(n)
        return result

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def merge_from_file(self, path: Path) -> None:
        """Additive merge from an external JSON file.

        Only adds codes/names that are not already present; never
        removes or overwrites existing entries.
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        incoming = raw.get("project_presets", {})
        if not isinstance(incoming, dict):
            return
        presets = self.settings.project_presets
        for code, names in incoming.items():
            code = str(code)
            if not isinstance(names, list):
                continue
            if code not in presets:
                presets[code] = []
            existing = set(presets[code])
            for n in names:
                n = str(n)
                if n not in existing:
                    presets[code].append(n)
                    existing.add(n)


# ---------------------------------------------------------------------------
# Module-level lazy singleton
# ---------------------------------------------------------------------------

_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    global _manager
    if _manager is None:
        _manager = SettingsManager()
    return _manager
