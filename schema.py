"""
schema.py — FEA Trace Authoritative Data Schema
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import re

SCHEMA_VERSION = "2.3.0"

class SolverType(str, Enum):
    IMPLICIT = "IMPLICIT"
    EXPLICIT = "EXPLICIT"
    MBD      = "MBD"

class RunStatus(str, Enum):
    WIP       = "WIP"
    CONVERGED = "converged"
    DIVERGED  = "diverged"
    PARTIAL   = "partial"
    ABORTED   = "aborted"

class VersionStatus(str, Enum):
    WIP        = "WIP"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"

VERSION_STATUS_TRANSITIONS: dict[VersionStatus, set[VersionStatus]] = {
    VersionStatus.WIP:        {VersionStatus.PRODUCTION, VersionStatus.DEPRECATED},
    VersionStatus.PRODUCTION: {VersionStatus.DEPRECATED, VersionStatus.WIP},
    VersionStatus.DEPRECATED: {VersionStatus.WIP},
}

RUN_STATUS_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.WIP:       {RunStatus.CONVERGED, RunStatus.DIVERGED,
                          RunStatus.PARTIAL,   RunStatus.ABORTED},
    RunStatus.CONVERGED: {RunStatus.WIP},
    RunStatus.DIVERGED:  {RunStatus.WIP},
    RunStatus.PARTIAL:   {RunStatus.WIP},
    RunStatus.ABORTED:   {RunStatus.WIP},
}

SOLVER_EXTENSIONS: dict[SolverType, str] = {
    SolverType.IMPLICIT: ".fem",
    SolverType.EXPLICIT: ".rad",
    SolverType.MBD:      ".xml",
}

REQUIRED_FOLDERS: list[str] = [
    "01_Source", "02_Models", "03_Runs", "04_Results", "90_Scripts",
]

VOWELS            = frozenset("AEIOU")
ENTITY_ID_MAX_LEN = 12

def generate_entity_id(name: str, existing_ids: list[str] | None = None) -> str:
    existing  = [e.upper() for e in (existing_ids or [])]
    cleaned   = re.sub(r"[^A-Z0-9]", "", name.upper())
    condensed = "".join(c for c in cleaned if c not in VOWELS)
    if not condensed:
        condensed = cleaned
    base      = condensed[:ENTITY_ID_MAX_LEN]
    candidate = base
    suffix    = 2
    while candidate in existing:
        suffix_str = f"_{suffix}"
        candidate  = base[:ENTITY_ID_MAX_LEN - len(suffix_str)] + suffix_str
        suffix    += 1
    return candidate

def next_version_id(existing: list[str]) -> str:
    nums = [int(v[1:]) for v in existing if re.fullmatch(r"V\d{2,}", v)]
    return f"V{(max(nums, default=0) + 1):02d}"

def next_iteration_id(existing: list[str]) -> str:
    nums = [int(i[1:]) for i in existing if re.fullmatch(r"I\d{2,}", i)]
    return f"I{(max(nums, default=0) + 1):02d}"

def next_run_id(existing: list[int]) -> int:
    return max(existing, default=0) + 1

def build_filename_base(project, entity_id, version_id, iter_id, solver_type) -> str:
    return f"{project}_{entity_id}_{version_id}{iter_id}_{solver_type.value}"

def build_run_filename(filename_base: str, run_id: int, solver_type: SolverType) -> str:
    return f"{filename_base}_{run_id:02d}{SOLVER_EXTENSIONS[solver_type]}"

@dataclass
class ArtifactRecord:
    input:  list[str] = field(default_factory=list)
    output: list[str] = field(default_factory=list)
    is_production: bool = False

@dataclass
class RunRecord:
    id:         int
    name:       str
    date:       str
    status:     RunStatus = RunStatus.WIP
    created_by: str = ""
    comments:   str = ""
    artifacts:  ArtifactRecord = field(default_factory=ArtifactRecord)
    MANDATORY = {"id", "name", "date", "status", "created_by"}

@dataclass
class IterationRecord:
    id:             str
    description:    str
    filename_base:  str
    created_by:     str
    created_on:     str
    solver_type:    SolverType = SolverType.IMPLICIT
    analysis_types: list[str] = field(default_factory=list)
    runs:           list[RunRecord] = field(default_factory=list)
    MANDATORY = {"id", "description", "filename_base", "created_by", "created_on",
                 "solver_type", "analysis_types"}

@dataclass
class VersionRecord:
    id:          str
    status:      VersionStatus
    description: str
    created_by:  str
    created_on:  str
    promoted_at: str = ""
    iterations:  list[IterationRecord] = field(default_factory=list)
    notes:       list[str] = field(default_factory=list)
    MANDATORY = {"id", "status", "description", "created_by", "created_on"}

@dataclass
class EntityRecord:
    id:         str
    name:       str
    project:    str
    owner_team: str
    created_by: str
    created_on: str
    versions:   list[VersionRecord] = field(default_factory=list)
    MANDATORY = {"id", "name", "project", "owner_team", "created_by", "created_on"}

@dataclass
class VersionLog:
    schema_version: str
    entity:         EntityRecord

def validate_status_transition(current, target):
    if isinstance(current, VersionStatus):
        table = VERSION_STATUS_TRANSITIONS
    else:
        table = RUN_STATUS_TRANSITIONS
    allowed = table.get(current, set())
    if target == current:
        return False, f"Already in status '{current.value}'."
    if target not in allowed:
        return False, (
            f"Transition '{current.value}' -> '{target.value}' is not permitted. "
            f"Allowed: {[s.value for s in allowed] or 'none'}."
        )
    return True, "OK"

def validate_mandatory_fields(record: object) -> list[str]:
    missing   = []
    mandatory = getattr(record, "MANDATORY", set())
    for f_name in mandatory:
        val = getattr(record, f_name, None)
        if val is None or val == "" or val == []:
            missing.append(f_name)
    return missing

def validate_filename(filename, entity, version_id, iteration, run_id):
    expected = build_run_filename(
        build_filename_base(entity.project, entity.id, version_id,
                            iteration.id, iteration.solver_type),
        run_id, iteration.solver_type,
    )
    if filename != expected:
        return False, f"Expected '{expected}', got '{filename}'."
    return True, "OK"
