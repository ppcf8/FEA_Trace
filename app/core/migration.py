from __future__ import annotations
from datetime import datetime
from typing import Callable
from packaging.version import Version
from app.config import TIMESTAMP_FORMAT

RawLog    = dict
MigrateFn = Callable[[RawLog, str], RawLog]

class MigrationRequired(Exception):
    def __init__(self, from_ver, to_ver, description):
        self.from_ver    = from_ver
        self.to_ver      = to_ver
        self.description = description
        super().__init__(f"Major migration required: {from_ver} -> {to_ver}. {description}")

class LogTooNew(Exception):
    def __init__(self, log_ver, tool_ver):
        self.log_ver  = log_ver
        self.tool_ver = tool_ver
        super().__init__(f"Log schema version {log_ver} is newer than this tool ({tool_ver}).")

MIGRATIONS: dict[str, tuple[MigrateFn, str, bool]] = {}

def _parse(v): return Version(v)

def _migration_chain(from_ver, tool_ver):
    chain, current = [], from_ver
    while _parse(current) < _parse(tool_ver):
        if current not in MIGRATIONS: break
        chain.append(current)
        test    = dict(MIGRATIONS[current][0]({"schema_version": current, "versions": []}, "__probe__"))
        current = test.get("schema_version", current)
        if current == chain[-1]: break
    return chain

def _migration_entry(from_ver, to_ver, migrated_by, notes):
    return {"from_version": from_ver, "to_version": to_ver,
            "migrated_by": migrated_by,
            "migrated_on": datetime.now().strftime(TIMESTAMP_FORMAT),
            "notes": notes}

def check(raw, tool_version):
    log_ver = raw.get("schema_version", "0.0.0")
    lv, tv  = _parse(log_ver), _parse(tool_version)
    if lv == tv: return "ok"
    if lv > tv:  return "too_new"
    chain = _migration_chain(log_ver, tool_version)
    if not chain: return "ok"
    for step in chain:
        _, _, is_major = MIGRATIONS[step]
        if is_major: return "confirm"
    return "auto"

def migrate(raw, tool_version, migrated_by, confirmed=False):
    log_ver = raw.get("schema_version", "0.0.0")
    lv, tv  = _parse(log_ver), _parse(tool_version)
    if lv > tv: raise LogTooNew(log_ver, tool_version)
    if lv == tv: return raw, []
    chain = _migration_chain(log_ver, tool_version)
    if not chain: return raw, []
    if not confirmed:
        for step in chain:
            fn, description, is_major = MIGRATIONS[step]
            if is_major:
                test   = dict(fn({"schema_version": step, "versions": []}, "__probe__"))
                target = test.get("schema_version", "unknown")
                raise MigrationRequired(step, target, description)
    notes = []
    if "migration_log" not in raw: raw["migration_log"] = []
    for step in chain:
        fn, description, _ = MIGRATIONS[step]
        before = raw.get("schema_version", step)
        raw    = fn(raw, migrated_by)
        after  = raw.get("schema_version", before)
        raw["migration_log"].append(_migration_entry(before, after, migrated_by, description))
        notes.append(f"{before} -> {after}: {description}")
    return raw, notes

def needs_migration(raw, tool_version):
    return check(raw, tool_version) in ("auto", "confirm")


# ---------------------------------------------------------------------------
# Migration: 1.0.0 → 2.0.0
# Flatten Representation → Iteration: solver_type and analysis_types moved
# to Iteration; Representation level removed.
# ---------------------------------------------------------------------------

def _migrate_1_0_0(raw: dict, migrated_by: str) -> dict:
    for ver in raw.get("versions", []):
        flat_iters = []
        new_id = 1
        for rep in ver.get("representations", []):
            solver_type    = rep.get("solver_type", "IMPLICIT")
            analysis_types = rep.get("analysis_types", [])
            for itr in rep.get("iterations", []):
                itr["solver_type"]    = solver_type
                itr["analysis_types"] = analysis_types
                itr["id"]             = f"I{new_id:02d}"
                # filename_base kept unchanged — files on disk must not be renamed
                flat_iters.append(itr)
                new_id += 1
        ver["iterations"] = flat_iters
        if "representations" in ver:
            del ver["representations"]
    raw["schema_version"] = "2.0.0"
    return raw


MIGRATIONS["1.0.0"] = (
    _migrate_1_0_0,
    "Flatten Representation→Iteration: solver_type and analysis_types moved to Iteration; "
    "Representation level removed.",
    True,
)


# ---------------------------------------------------------------------------
# Migration: 2.0.0 → 2.1.0
# Remove design_changes field from iterations (redundant with description).
# ---------------------------------------------------------------------------

def _migrate_2_0_0(raw: dict, migrated_by: str) -> dict:
    for ver in raw.get("versions", []):
        for itr in ver.get("iterations", []):
            itr.pop("design_changes", None)
    raw["schema_version"] = "2.1.0"
    return raw


MIGRATIONS["2.0.0"] = (
    _migrate_2_0_0,
    "Remove design_changes field from iterations (redundant with description).",
    False,
)


# ---------------------------------------------------------------------------
# Migration: 2.1.0 → 2.2.0
# Rename VersionRecord.intent → description.
# ---------------------------------------------------------------------------

def _migrate_2_1_0(raw: dict, migrated_by: str) -> dict:
    for ver in raw.get("versions", []):
        if "intent" in ver:
            ver["description"] = ver.pop("intent")
    raw["schema_version"] = "2.2.0"
    return raw


MIGRATIONS["2.1.0"] = (
    _migrate_2_1_0,
    "Rename VersionRecord.intent → description.",
    False,
)


# ---------------------------------------------------------------------------
# Migration: 2.2.0 → 2.3.0
# Add promoted_at timestamp field to VersionRecord.
# ---------------------------------------------------------------------------

def _migrate_2_2_0(raw: dict, migrated_by: str) -> dict:
    for v in raw.get("versions", []):
        v.setdefault("promoted_at", "")
    raw["schema_version"] = "2.3.0"
    return raw


MIGRATIONS["2.2.0"] = (
    _migrate_2_2_0,
    "Add promoted_at timestamp to VersionRecord.",
    False,   # minor — auto-applied
)


# ---------------------------------------------------------------------------
# Migration: 2.3.0 → 2.4.0
# Add status and notes fields to IterationRecord.
# ---------------------------------------------------------------------------

def _migrate_2_3_0(raw: dict, migrated_by: str) -> dict:
    for ver in raw.get("versions", []):
        for itr in ver.get("iterations", []):
            itr.setdefault("status", "WIP")
            itr.setdefault("notes", [])
    raw["schema_version"] = "2.4.0"
    return raw


MIGRATIONS["2.3.0"] = (
    _migrate_2_3_0,
    "Add status and notes fields to IterationRecord.",
    False,   # minor — auto-applied
)


# ---------------------------------------------------------------------------
# Migration: 2.4.0 → 2.5.0
# Move promoted_at from VersionRecord to IterationRecord.
# Iterations with is_production runs gain status="production" and inherit
# the version's promoted_at timestamp.
# ---------------------------------------------------------------------------

def _migrate_2_4_0(raw: dict, migrated_by: str) -> dict:
    for v in raw.get("versions", []):
        v_promoted_at = v.pop("promoted_at", "")
        for itr in v.get("iterations", []):
            has_prod = any(r.get("artifacts", {}).get("is_production", False)
                           for r in itr.get("runs", []))
            if has_prod:
                itr["status"] = "production"
                itr.setdefault("promoted_at", v_promoted_at)
            else:
                itr.setdefault("promoted_at", "")
    raw["schema_version"] = "2.5.0"
    return raw


MIGRATIONS["2.4.0"] = (
    _migrate_2_4_0,
    "Move promoted_at from VersionRecord to IterationRecord; "
    "mark iterations with production runs as IterationStatus.PRODUCTION.",
    False,   # minor — auto-applied
)


# ---------------------------------------------------------------------------
# Migration: 2.5.0 → 2.6.0
# Add communications list to VersionRecord.
# ---------------------------------------------------------------------------

def _migrate_2_5_0(raw: dict, migrated_by: str) -> dict:
    for v in raw.get("versions", []):
        v.setdefault("communications", [])
    raw["schema_version"] = "2.6.0"
    return raw


MIGRATIONS["2.5.0"] = (
    _migrate_2_5_0,
    "Add communications list to VersionRecord.",
    False,   # minor — auto-applied
)


# ---------------------------------------------------------------------------
# Migration: 2.6.0 → 2.7.0
# Rename eml_filename (str) → eml_filenames (list[str]) in CommunicationRecord.
# ---------------------------------------------------------------------------

def _migrate_2_6_0(raw: dict, migrated_by: str) -> dict:
    for v in raw.get("versions", []):
        for c in v.get("communications", []):
            if "eml_filenames" not in c:
                old = c.pop("eml_filename", "")
                c["eml_filenames"] = [old] if old else []
    raw["schema_version"] = "2.7.0"
    return raw


MIGRATIONS["2.6.0"] = (
    _migrate_2_6_0,
    "Rename eml_filename → eml_filenames (list) in CommunicationRecord.",
    False,   # minor — auto-applied
)


# ---------------------------------------------------------------------------
# Migration: 2.7.0 → 2.8.0
# Add source_components list to VersionRecord.
# ---------------------------------------------------------------------------

def _migrate_2_7_0(raw: dict, migrated_by: str) -> dict:
    for v in raw.get("versions", []):
        v.setdefault("source_components", [])
    raw["schema_version"] = "2.8.0"
    return raw


MIGRATIONS["2.7.0"] = (
    _migrate_2_7_0,
    "Add source_components list to VersionRecord.",
    False,   # minor — auto-applied
)
