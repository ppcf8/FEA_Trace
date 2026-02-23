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
