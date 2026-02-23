from __future__ import annotations
import os, socket, yaml
from datetime import datetime
from pathlib import Path
from typing import Optional
from schema import (
    SCHEMA_VERSION, SolverType, RunStatus, VersionStatus,
    VERSION_STATUS_TRANSITIONS, RUN_STATUS_TRANSITIONS,
    REQUIRED_FOLDERS, SOLVER_EXTENSIONS, generate_entity_id,
    next_version_id, next_iteration_id, next_run_id,
    build_filename_base, build_run_filename,
    validate_status_transition, validate_mandatory_fields,
    ArtifactRecord, RunRecord, IterationRecord,
    VersionRecord, EntityRecord, VersionLog,
)
from app.config import (
    LOCK_TIMEOUT_SECONDS, LOCK_FILENAME, LOG_FILENAME,
    REQUIRED_PRODUCTION_ARTIFACTS, RUNS_FOLDER, RESULTS_FOLDER,
    TIMESTAMP_FORMAT,
)

class FEATraceError(Exception): pass
class LockError(FEATraceError): pass
class ValidationError(FEATraceError): pass
class MigrationError(FEATraceError): pass
class StatusTransitionError(FEATraceError): pass

def _now(): return datetime.now().strftime(TIMESTAMP_FORMAT)
def _current_user():
    try: return os.getlogin()
    except Exception: return os.environ.get("USERNAME", "unknown")
def _current_host(): return socket.gethostname()

class _LockManager:
    def __init__(self, entity_path):
        self._lock_path = entity_path / LOCK_FILENAME
        self.warning    = None
    def __enter__(self):
        if self._lock_path.exists():
            age = (datetime.now() - datetime.fromtimestamp(
                self._lock_path.stat().st_mtime)).total_seconds()
            if age < LOCK_TIMEOUT_SECONDS:
                info = self._read_lock_info()
                raise LockError(
                    f"Locked by {info.get('locked_by','unknown')} "
                    f"on {info.get('hostname','unknown')} "
                    f"since {info.get('timestamp','unknown')}.")
            else:
                self.warning = f"Stale lock (age {age:.0f}s). Overwriting."
        self._write_lock()
        return self
    def __exit__(self, *_):
        try: self._lock_path.unlink(missing_ok=True)
        except OSError: pass
    def _write_lock(self):
        import yaml as _yaml
        self._lock_path.write_text(
            _yaml.dump({"locked_by": _current_user(), "hostname": _current_host(),
                        "timestamp": _now(), "pid": os.getpid()}), encoding="utf-8")
    def _read_lock_info(self):
        try: return yaml.safe_load(self._lock_path.read_text(encoding="utf-8")) or {}
        except Exception: return {}

def _deserialise_run(raw):
    arts = raw.get("artifacts", {})
    return RunRecord(
        id=int(raw["id"]), name=raw["name"], date=raw["date"],
        status=RunStatus(raw["status"]),
        created_by=raw.get("created_by",""), comments=raw.get("comments",""),
        artifacts=ArtifactRecord(
            input=arts.get("input",[]), output=arts.get("output",[]),
            is_production=arts.get("is_production", False)),
    )

def _deserialise_iteration(raw):
    return IterationRecord(
        id=raw["id"], description=raw["description"],
        filename_base=raw["filename_base"],
        created_by=raw["created_by"], created_on=raw["created_on"],
        solver_type=SolverType(raw.get("solver_type", "IMPLICIT")),
        analysis_types=raw.get("analysis_types", []),
        design_changes=raw.get("design_changes",[]),
        runs=[_deserialise_run(r) for r in raw.get("runs",[])])

def _deserialise_version(raw):
    return VersionRecord(
        id=raw["id"], status=VersionStatus(raw["status"]),
        intent=raw["intent"], created_by=raw["created_by"], created_on=raw["created_on"],
        iterations=[_deserialise_iteration(i) for i in raw.get("iterations",[])],
        notes=raw.get("notes",[]))

def _load_log(log_path):
    try: raw = yaml.safe_load(log_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValidationError(f"YAML parse error: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValidationError(f"{log_path} is not a valid YAML mapping.")
    er = raw.get("entity", {})
    entity = EntityRecord(
        id=er.get("id",""), name=er.get("name",""), project=er.get("project",""),
        owner_team=er.get("owner_team",""), created_by=er.get("created_by",""),
        created_on=er.get("created_on",""),
        versions=[_deserialise_version(v) for v in raw.get("versions",[])])
    log = VersionLog(schema_version=raw.get("schema_version",""), entity=entity)
    _validate_log(log)
    return log

def _serialise_log(log):
    def run_d(r): return {"id":r.id,"name":r.name,"date":r.date,"status":r.status.value,
        "created_by":r.created_by,"comments":r.comments,
        "artifacts":{"input":r.artifacts.input,"output":r.artifacts.output,
                     "is_production":r.artifacts.is_production}}
    def iter_d(i): return {"id":i.id,"description":i.description,
        "filename_base":i.filename_base,"created_by":i.created_by,"created_on":i.created_on,
        "solver_type":i.solver_type.value,"analysis_types":i.analysis_types,
        "design_changes":i.design_changes,"runs":[run_d(r) for r in i.runs]}
    def ver_d(v): return {"id":v.id,"status":v.status.value,"intent":v.intent,
        "created_by":v.created_by,"created_on":v.created_on,"notes":v.notes,
        "iterations":[iter_d(i) for i in v.iterations]}
    e = log.entity
    return {"schema_version":log.schema_version,
            "entity":{"id":e.id,"name":e.name,"project":e.project,
                      "owner_team":e.owner_team,"created_by":e.created_by,"created_on":e.created_on},
            "versions":[ver_d(v) for v in e.versions]}

def _write_log(log_path, log):
    tmp = log_path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.dump(_serialise_log(log), allow_unicode=True,
                             sort_keys=False, default_flow_style=False), encoding="utf-8")
    tmp.replace(log_path)

def _validate_log(log):
    errors = []
    for rec, label in [(log.entity, "Entity")]:
        m = validate_mandatory_fields(rec)
        if m: errors.append(f"{label} missing: {m}")
    for v in log.entity.versions:
        m = validate_mandatory_fields(v)
        if m: errors.append(f"Version {v.id} missing: {m}")
        for i in v.iterations:
            m = validate_mandatory_fields(i)
            if m: errors.append(f"Iter {v.id}/{i.id} missing: {m}")
            for run in i.runs:
                m = validate_mandatory_fields(run)
                if m: errors.append(f"Run {v.id}/{i.id}/{run.id} missing: {m}")
    if errors:
        raise ValidationError("Log validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

def _validate_folder_anatomy(entity_path):
    return [f"Missing required folder: {f}"
            for f in REQUIRED_FOLDERS if not (entity_path / f).is_dir()]

def _check_production_artifacts(entity_path, solver_type, filename_base, run_id):
    warnings, required = [], REQUIRED_PRODUCTION_ARTIFACTS.get(solver_type, [])
    base = f"{filename_base}_{run_id:02d}"
    for ext in required:
        folder = RUNS_FOLDER if ext == SOLVER_EXTENSIONS[solver_type] else RESULTS_FOLDER
        target = entity_path / folder / f"{base}{ext}"
        if not target.exists():
            warnings.append(f"Missing: {target.relative_to(entity_path)}")
    return warnings

class FEAProject:
    def __init__(self, entity_path, log):
        self._path = entity_path
        self._log  = log

    @property
    def entity(self): return self._log.entity
    @property
    def path(self):   return self._path

    @classmethod
    def create(cls, parent_dir, name, project, owner_team, created_by, existing_ids=None):
        parent_dir  = Path(parent_dir)
        entity_id   = generate_entity_id(name, existing_ids)
        folder_name = f"{project}_{name.replace(' ','_')}"
        entity_path = parent_dir / folder_name
        if entity_path.exists():
            raise ValidationError(f"Entity folder already exists: {entity_path}")
        entity_path.mkdir(parents=True)
        for folder in REQUIRED_FOLDERS:
            (entity_path / folder).mkdir()
        entity   = EntityRecord(id=entity_id, name=name, project=project,
                                owner_team=owner_team, created_by=created_by, created_on=_now())
        log      = VersionLog(schema_version=SCHEMA_VERSION, entity=entity)
        instance = cls(entity_path, log)
        instance._write()
        return instance

    @classmethod
    def load(cls, entity_path):
        entity_path = Path(entity_path)
        log_path    = entity_path / LOG_FILENAME
        if not log_path.exists():
            raise ValidationError(f"No {LOG_FILENAME} found in {entity_path}.")
        log      = _load_log(log_path)
        warnings = _validate_folder_anatomy(entity_path)
        return cls(entity_path, log), warnings

    def add_version(self, intent, created_by, notes=None):
        existing = [v.id for v in self._log.entity.versions]
        v = VersionRecord(id=next_version_id(existing), status=VersionStatus.WIP,
                          intent=intent, created_by=created_by, created_on=_now(),
                          notes=notes or [])
        self._log.entity.versions.append(v)
        self._write(); return v

    def update_version_status(self, version_id, new_status, revert_reason=None):
        v = self._get_version(version_id)
        ok, reason = validate_status_transition(v.status, new_status)
        if not ok: raise StatusTransitionError(reason)
        if new_status == VersionStatus.WIP and v.status != VersionStatus.WIP:
            if not revert_reason:
                raise ValidationError("A reason is required when reverting to WIP.")
            v.notes.append(
                f"[REVERTED to WIP from {v.status.value} "
                f"by {_current_user()} on {_now()}] {revert_reason}")
        v.status = new_status
        self._write()

    def add_iteration(self, version_id, solver_type, analysis_types,
                      description, created_by, design_changes=None):
        v        = self._get_version(version_id)
        existing = [i.id for i in v.iterations]
        iter_id  = next_iteration_id(existing)
        fname    = build_filename_base(self._log.entity.project, self._log.entity.id,
                                       version_id, iter_id, solver_type)
        i = IterationRecord(id=iter_id, description=description, filename_base=fname,
                            created_by=created_by, created_on=_now(),
                            solver_type=solver_type, analysis_types=analysis_types,
                            design_changes=design_changes or [])
        v.iterations.append(i); self._write(); return i

    def add_run(self, version_id, iter_id, created_by, comments=""):
        v      = self._get_version(version_id)
        i      = self._get_iteration(v, iter_id)
        run_id = next_run_id([run.id for run in i.runs])
        run_name = build_run_filename(i.filename_base, run_id, i.solver_type)
        run = RunRecord(id=run_id, name=run_name, date=_now(), status=RunStatus.WIP,
                        created_by=created_by, comments=comments,
                        artifacts=ArtifactRecord(input=[SOLVER_EXTENSIONS[i.solver_type]]))
        i.runs.append(run); self._write()
        run_folder = self._path / RUNS_FOLDER / f"Run_{run_id:02d}"
        run_folder.mkdir(parents=True, exist_ok=True)
        return run

    def update_run_status(self, version_id, iter_id, run_id,
                          new_status, comments="", output_artifacts=None, is_production=None):
        """Transitions run to a new status. Same-status calls are blocked — use
        update_run_comments() for comment/artifact-only updates."""
        v   = self._get_version(version_id)
        i   = self._get_iteration(v, iter_id)
        run = self._get_run(i, run_id)
        ok, reason = validate_status_transition(run.status, new_status)
        if not ok: raise StatusTransitionError(reason)
        run.status = new_status
        if comments:                     run.comments             = comments
        if output_artifacts is not None: run.artifacts.output     = output_artifacts
        if is_production is not None:    run.artifacts.is_production = is_production
        warnings = (_check_production_artifacts(
                        self._path, i.solver_type, i.filename_base, run_id)
                    if run.artifacts.is_production else [])
        self._write(); return warnings

    def update_run_comments(self, version_id, iter_id, run_id,
                            comments=None, output_artifacts=None, is_production=None):
        """
        Updates mutable run fields (comments, output artifacts, production flag)
        without changing status. Safe to call on runs in any status.
        Returns production artifact warnings if is_production is True.
        """
        v   = self._get_version(version_id)
        i   = self._get_iteration(v, iter_id)
        run = self._get_run(i, run_id)
        if comments is not None:         run.comments             = comments
        if output_artifacts is not None: run.artifacts.output     = output_artifacts
        if is_production is not None:    run.artifacts.is_production = is_production
        warnings = (_check_production_artifacts(
                        self._path, i.solver_type, i.filename_base, run_id)
                    if run.artifacts.is_production else [])
        self._write(); return warnings

    def update_production_flag(self, version_id, iter_id, run_id, is_production):
        v   = self._get_version(version_id)
        i   = self._get_iteration(v, iter_id)
        run = self._get_run(i, run_id)
        run.artifacts.is_production = is_production
        warnings = (_check_production_artifacts(
                        self._path, i.solver_type, i.filename_base, run_id)
                    if is_production else [])
        self._write(); return warnings

    def get_latest_version(self):
        return self._log.entity.versions[-1] if self._log.entity.versions else None

    def _get_version(self, vid):
        for v in self._log.entity.versions:
            if v.id == vid: return v
        raise ValidationError(f"Version '{vid}' not found.")

    def _get_iteration(self, version, iid):
        for i in version.iterations:
            if i.id == iid: return i
        raise ValidationError(f"Iteration '{iid}' not found in {version.id}.")

    def _get_run(self, iteration, run_id):
        for run in iteration.runs:
            if run.id == run_id: return run
        raise ValidationError(f"Run '{run_id}' not found in {iteration.id}.")

    def _write(self):
        with _LockManager(self._path) as lock:
            if lock.warning: self._last_lock_warning = lock.warning
            _write_log(self._path / LOG_FILENAME, self._log)

    _last_lock_warning: Optional[str] = None
