from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

SESSION_VERSION    = "1.0"
DEFAULT_SESSION_DIR = Path.home() / "Documents" / "FEA_Trace"

class SessionManager:
    def __init__(self):
        self._path:     Optional[Path] = None
        self._entities: list[str]      = []

    @property
    def path(self): return self._path
    @property
    def entities(self): return list(self._entities)
    @property
    def has_file(self): return self._path is not None
    @property
    def display_name(self): return self._path.name if self._path else "Unsaved Session"

    def load(self, path) -> list[str]:
        path = Path(path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Cannot read session file: {exc}") from exc
        if not isinstance(raw, dict) or "entities" not in raw:
            raise ValueError("Not a valid FEA Trace session file.")
        valid = [e for e in raw.get("entities", []) if Path(e).is_dir()]
        self._path     = path
        self._entities = valid
        return valid

    def save(self):
        if self._path is None:
            raise RuntimeError("No session file path set.")
        self._write(self._path)

    def save_as(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write(path)
        self._path = path

    def _write(self, path):
        path.write_text(
            json.dumps({"version": SESSION_VERSION, "entities": self._entities},
                       indent=2, ensure_ascii=False),
            encoding="utf-8")

    def set_entities(self, paths): self._entities = list(paths)
    def add_entity(self, path):
        p = str(Path(path))
        if p not in self._entities: self._entities.append(p)
    def remove_entity(self, path):
        p = str(Path(path))
        self._entities = [e for e in self._entities if e != p]
    def clear(self):
        self._entities = []
        self._path     = None
