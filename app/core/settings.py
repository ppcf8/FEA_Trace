"""
app/core/settings.py — User preference persistence (project-code & entity-name presets).

Each preset entry is a dict {"name": str, "id": str} where id may be "".
The JSON on disk omits the "id" key when it is empty to keep files readable.

Backward compatibility: if a settings.json written by the old version contains
plain strings instead of dicts, they are silently promoted to {"name": s, "id": ""}.
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
    project_presets: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    # {"PROJ_A": [{"name": "Wing", "id": "WNG"}, {"name": "Fuselage", "id": ""}], …}


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
            incoming = raw.get("project_presets", {})
            if not isinstance(incoming, dict):
                return
            result: dict[str, list[dict[str, str]]] = {}
            for code, entries in incoming.items():
                if not isinstance(entries, list):
                    continue
                parsed: list[dict[str, str]] = []
                for e in entries:
                    if isinstance(e, str):
                        # backward compat: plain string → name-only entry
                        if e.strip():
                            parsed.append({"name": e.strip(), "id": ""})
                    elif isinstance(e, dict):
                        name = str(e.get("name", "")).strip()
                        eid  = str(e.get("id",   "")).strip()
                        if name:
                            parsed.append({"name": name, "id": eid})
                result[str(code)] = parsed
            self.settings.project_presets = result
        except Exception:
            # Silently ignore corrupt / unreadable settings
            pass

    def save(self) -> None:
        _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        # Omit "id" key when empty to keep JSON files clean
        serializable: dict[str, list] = {
            code: [
                ({"name": e["name"], "id": e["id"]} if e.get("id") else {"name": e["name"]})
                for e in entries
            ]
            for code, entries in self.settings.project_presets.items()
        }
        _SETTINGS_PATH.write_text(
            json.dumps({"project_presets": serializable}, indent=2, ensure_ascii=False),
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
            return [e["name"] for e in presets[project_code]]
        # Fallback: union of all names, preserving insertion order
        seen: set[str] = set()
        result: list[str] = []
        for entries in presets.values():
            for e in entries:
                n = e["name"]
                if n not in seen:
                    seen.add(n)
                    result.append(n)
        return result

    def entity_id_for(self, project_code: str, name: str) -> str:
        """Return the preset entity ID for a given (project_code, name) pair, or ''."""
        for entry in self.settings.project_presets.get(project_code, []):
            if entry["name"] == name:
                return entry.get("id", "")
        return ""

    def add_preset_entry(self, project_code: str, name: str, entity_id: str = "") -> None:
        """Add or update a preset entry (in-memory only — call save() to persist).

        - Creates the project code bucket if it does not yet exist.
        - If an entry with the same name already exists, updates its id
          (only when entity_id is non-empty).
        """
        presets = self.settings.project_presets
        if project_code not in presets:
            presets[project_code] = []
        for entry in presets[project_code]:
            if entry["name"] == name:
                if entity_id:
                    entry["id"] = entity_id
                return
        presets[project_code].append({"name": name, "id": entity_id})

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def merge_from_file(self, path: Path) -> None:
        """Additive merge from an external JSON file.

        Only adds codes/names not already present; never removes or
        overwrites existing entries.  Handles both old (string) and
        new (dict) entry formats.
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        incoming = raw.get("project_presets", {})
        if not isinstance(incoming, dict):
            return
        presets = self.settings.project_presets
        for code, entries in incoming.items():
            code = str(code)
            if not isinstance(entries, list):
                continue
            if code not in presets:
                presets[code] = []
            existing_names = {e["name"] for e in presets[code]}
            for e in entries:
                if isinstance(e, str):
                    name, eid = e.strip(), ""
                elif isinstance(e, dict):
                    name = str(e.get("name", "")).strip()
                    eid  = str(e.get("id",   "")).strip()
                else:
                    continue
                if name and name not in existing_names:
                    presets[code].append({"name": name, "id": eid})
                    existing_names.add(name)


# ---------------------------------------------------------------------------
# Module-level lazy singleton
# ---------------------------------------------------------------------------

_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    global _manager
    if _manager is None:
        _manager = SettingsManager()
    return _manager
