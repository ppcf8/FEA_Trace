from __future__ import annotations
import os, socket, yaml
from datetime import datetime
from pathlib import Path
from typing import Optional
from schema import (
    SCHEMA_VERSION, SolverType, RunStatus, IterationStatus, VersionStatus,
    ITERATION_STATUS_TRANSITIONS, VERSION_STATUS_TRANSITIONS, RUN_STATUS_TRANSITIONS,
    REQUIRED_FOLDERS, SOLVER_EXTENSIONS, generate_entity_id,
    next_version_id, next_iteration_id, next_run_id,
    build_filename_base, build_run_filename,
    validate_status_transition, validate_mandatory_fields,
    ArtifactRecord, CommunicationRecord, SourceComponentRecord,
    RunRecord, IterationRecord, VersionRecord, EntityRecord, VersionLog,
)
from app.config import (
    LOCK_TIMEOUT_SECONDS, LOCK_FILENAME, LOG_FILENAME,
    REQUIRED_PRODUCTION_ARTIFACTS, RUNS_FOLDER, RESULTS_FOLDER,
    TIMESTAMP_FORMAT, SOURCE_FOLDER,
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
        status=IterationStatus(raw.get("status", "WIP")),
        notes=raw.get("notes", []),
        promoted_at=raw.get("promoted_at", ""),
        runs=[_deserialise_run(r) for r in raw.get("runs",[])])

def _deserialise_comm(raw):
    return CommunicationRecord(
        sent_at=raw["sent_at"], sent_by=raw["sent_by"],
        to=raw["to"], subject=raw["subject"],
        body_summary=raw.get("body_summary", ""),
        eml_filenames=raw.get("eml_filenames",
            [raw["eml_filename"]] if raw.get("eml_filename") else []),
        run_refs=raw.get("run_refs", []))

def _deserialise_source_component(raw):
    return SourceComponentRecord(
        entity_path=raw["entity_path"], entity_name=raw["entity_name"],
        project_code=raw["project_code"], version_id=raw["version_id"],
        copied_files=raw.get("copied_files", []))

def _deserialise_version(raw):
    return VersionRecord(
        id=raw["id"], status=VersionStatus(raw["status"]),
        description=raw["description"], created_by=raw["created_by"], created_on=raw["created_on"],
        iterations=[_deserialise_iteration(i) for i in raw.get("iterations",[])],
        notes=raw.get("notes",[]),
        communications=[_deserialise_comm(c) for c in raw.get("communications", [])],
        source_components=[_deserialise_source_component(s)
                           for s in raw.get("source_components", [])])

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
        "status":i.status.value,"notes":i.notes,"promoted_at":i.promoted_at,
        "runs":[run_d(r) for r in i.runs]}
    def comm_d(c): return {"sent_at":c.sent_at,"sent_by":c.sent_by,
        "to":c.to,"subject":c.subject,"body_summary":c.body_summary,
        "eml_filenames":c.eml_filenames,"run_refs":c.run_refs}
    def sc_d(s): return {"entity_path":s.entity_path,"entity_name":s.entity_name,
        "project_code":s.project_code,"version_id":s.version_id,
        "copied_files":s.copied_files}
    def ver_d(v): return {"id":v.id,"status":v.status.value,"description":v.description,
        "created_by":v.created_by,"created_on":v.created_on,
        "notes":v.notes,
        "communications":[comm_d(c) for c in v.communications],
        "source_components":[sc_d(s) for s in v.source_components],
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

def _run_subfolder(version_id, iter_id, run_id):
    """Return the run subfolder name, e.g. 'V01I01_Run_01'."""
    return f"{version_id}{iter_id}_Run_{run_id:02d}"

def _supports_trash(path: Path) -> bool:
    """Return True if *path* is on a drive that supports the OS Recycle Bin.

    Network drives (mapped or UNC) do not have a Recycle Bin on Windows; sending
    files there via send2trash silently permanently deletes them. This helper
    detects that case so callers can warn the user and use shutil.rmtree instead.
    Falls back to True on any error so that send2trash gets the first attempt.
    """
    try:
        import ctypes
        path_str = str(path)
        if path_str.startswith("\\\\"):   # UNC path (\\server\share\…)
            return False
        drive = Path(path_str).drive      # e.g. 'C:'
        if not drive:
            return True
        DRIVE_REMOTE = 4
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive + "\\")
        return drive_type != DRIVE_REMOTE
    except Exception:
        return True  # unknown — let send2trash attempt and raise if needed

def _check_production_artifacts(entity_path, solver_type, filename_base, run_id,
                                version_id, iter_id, output_artifacts=None):
    warnings = []
    base     = f"{filename_base}_{run_id:02d}"
    run_dir  = entity_path / RUNS_FOLDER / _run_subfolder(version_id, iter_id, run_id)
    required = REQUIRED_PRODUCTION_ARTIFACTS.get(solver_type, [])

    # Always check every artifact defined in config (input deck + config outputs)
    for ext in required:
        target = run_dir / f"{base}{ext}"
        if not target.exists():
            warnings.append(f"Missing: {target.relative_to(entity_path)}")

    # Also check any user-defined extras not already covered by config
    for ext in (output_artifacts or []):
        if ext not in required:
            target = run_dir / f"{base}{ext}"
            if not target.exists():
                warnings.append(f"Missing: {target.relative_to(entity_path)}")

    return warnings

def _check_input_file(entity_path, solver_type, filename_base, run_id,
                      version_id, iter_id):
    """Check whether the solver deck (input file) exists in the run subfolder."""
    ext    = SOLVER_EXTENSIONS[solver_type]
    base   = f"{filename_base}_{run_id:02d}"
    target = entity_path / RUNS_FOLDER / _run_subfolder(version_id, iter_id, run_id) / f"{base}{ext}"
    if not target.exists():
        return [f"Missing: {target.relative_to(entity_path)}"]
    return []

class FEAProject:
    def __init__(self, entity_path, log):
        self._path = entity_path
        self._log  = log

    @property
    def entity(self): return self._log.entity
    @property
    def path(self):   return self._path

    @classmethod
    def create(cls, parent_dir, name, project, owner_team, created_by,
               existing_ids=None, entity_id=None):
        parent_dir = Path(parent_dir)
        entity_id  = entity_id or generate_entity_id(name, existing_ids)
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

    def add_version(self, description, created_by, notes=None, source_components=None):
        existing = [v.id for v in self._log.entity.versions]
        v = VersionRecord(id=next_version_id(existing), status=VersionStatus.WIP,
                          description=description, created_by=created_by, created_on=_now(),
                          notes=notes or [], source_components=source_components or [])
        self._log.entity.versions.append(v)
        self._write(); return v

    def copy_version_source_files(self, version_id: str, step_files: list) -> Path:
        """Copy STEP files into {entity_path}/01_Source/{version_id}/.
        Returns destination folder. Collision-safe: appends _2, _3, … when needed."""
        import shutil
        dest_folder = self._path / SOURCE_FOLDER / version_id
        dest_folder.mkdir(parents=True, exist_ok=True)
        for src in step_files:
            src  = Path(src)
            dest = dest_folder / src.name
            if not dest.exists():
                shutil.copy2(src, dest)
            else:
                stem, suffix = src.stem, src.suffix
                n = 2
                while dest.exists():
                    dest = dest_folder / f"{stem}_{n}{suffix}"
                    n += 1
                shutil.copy2(src, dest)
        return dest_folder

    def get_version_source_folder(self, version_id: str) -> Path:
        """Returns {entity_path}/01_Source/{version_id}/ without creating it."""
        return self._path / SOURCE_FOLDER / version_id

    def update_version_status(self, version_id, new_status,
                              revert_reason=None, deprecation_reason=None):
        v = self._get_version(version_id)
        ok, reason = validate_status_transition(v.status, new_status)
        if not ok: raise StatusTransitionError(reason)
        if new_status == VersionStatus.PRODUCTION:
            has_prod_iter = any(i.status == IterationStatus.PRODUCTION for i in v.iterations)
            if not has_prod_iter:
                raise ValidationError(
                    "Cannot mark version as Production — "
                    "at least one iteration must be promoted to Production first.")
        if new_status == VersionStatus.WIP and v.status != VersionStatus.WIP:
            if not revert_reason:
                raise ValidationError("A reason is required when reverting to WIP.")
            v.notes.append(
                f"[Reverted to WIP] from {v.status.value} on {_now()} "
                f"by {_current_user()} — {revert_reason}")
        if new_status == VersionStatus.DEPRECATED:
            if not deprecation_reason:
                raise ValidationError("A reason is required when deprecating.")
            v.notes.append(
                f"[Deprecated] on {_now()} by {_current_user()} — {deprecation_reason}")
        v.status = new_status
        self._write()

    def update_iteration_status(self, version_id, iter_id, target,
                                revert_reason=None, deprecation_reason=None):
        v = self._get_version(version_id)
        i = self._get_iteration(v, iter_id)
        ok, reason = validate_status_transition(i.status, target)
        if not ok: raise StatusTransitionError(reason)
        if target == IterationStatus.WIP and i.status != IterationStatus.WIP:
            if not revert_reason:
                raise ValidationError("A reason is required when reverting to WIP.")
            i.notes.append(
                f"[Reverted to WIP] from {i.status.value} on {_now()} "
                f"by {_current_user()} — {revert_reason}")
            if i.status == IterationStatus.PRODUCTION:
                i.promoted_at = ""
                for run in i.runs:
                    run.artifacts.is_production = False
        if target == IterationStatus.DEPRECATED:
            if not deprecation_reason:
                raise ValidationError("A reason is required when deprecating.")
            i.notes.append(
                f"[Deprecated] on {_now()} by {_current_user()} — {deprecation_reason}")
        i.status = target
        self._write()

    def revert_iteration_to_wip(self, version_id: str, iter_id: str, reason: str) -> None:
        """Revert a PRODUCTION or DEPRECATED iteration to WIP with a mandatory reason."""
        self.update_iteration_status(
            version_id, iter_id, IterationStatus.WIP, revert_reason=reason
        )

    def promote_iteration_to_production(
            self, version_id: str, iter_id: str,
            production_run_ids: list[int],
    ) -> dict:
        """Promote a single iteration to PRODUCTION and mark selected runs.
        Clears any previously set is_production flags in this iteration first,
        then marks the selected run_ids. Returns artifact warnings dict."""
        v = self._get_version(version_id)
        i = self._get_iteration(v, iter_id)
        ok, reason = validate_status_transition(i.status, IterationStatus.PRODUCTION)
        if not ok:
            raise StatusTransitionError(reason)
        # Block if any run in this iteration is still WIP
        wip_runs = [run.id for run in i.runs if run.status == RunStatus.WIP]
        if wip_runs:
            raise ValidationError(
                f"Cannot promote — resolve WIP runs first: "
                f"{', '.join(f'Run {r:02d}' for r in wip_runs)}")
        now = _now()
        # Clear all existing flags, then re-mark selected
        for run in i.runs:
            run.artifacts.is_production = False
        warnings: dict = {}
        for run_id in production_run_ids:
            run = self._get_run(i, run_id)
            run.artifacts.is_production = True
            w = _check_production_artifacts(
                self._path, i.solver_type, i.filename_base,
                run_id, version_id, iter_id, run.artifacts.output)
            if w:
                warnings[run_id] = w
        i.status      = IterationStatus.PRODUCTION
        i.promoted_at = now
        run_list_str  = ", ".join(f"Run {r:02d}" for r in sorted(production_run_ids))
        i.notes.append(
            f"[Promoted to Production] on {now} by {_current_user()} — Runs: {run_list_str}")
        self._write()
        return warnings

    def delete_run(self, version_id: str, iter_id: str, run_id: int,
                   trash_folder: bool = True) -> None:
        """Remove a run record from the log and optionally delete its folder.

        When trash_folder is True:
          - Local drives: folder is sent to the OS Recycle Bin via send2trash.
          - Network / UNC drives: folder is permanently deleted via shutil.rmtree
            (network drives have no Recycle Bin).
        When trash_folder is False the folder is left untouched on disk.
        """
        v   = self._get_version(version_id)
        i   = self._get_iteration(v, iter_id)
        self._get_run(i, run_id)  # raises ValidationError if not found
        i.runs = [r for r in i.runs if r.id != run_id]
        if trash_folder:
            run_folder = self._path / RUNS_FOLDER / _run_subfolder(version_id, iter_id, run_id)
            if run_folder.exists():
                if _supports_trash(run_folder):
                    from send2trash import send2trash
                    send2trash(str(run_folder))
                else:
                    import shutil
                    shutil.rmtree(run_folder)
        self._write()

    def update_entity_metadata(self, name, project, owner_team, created_by):
        e = self._log.entity
        e.name       = name
        e.project    = project
        e.owner_team = owner_team
        e.created_by = created_by
        self._write()

    def update_version_metadata(self, version_id, description, notes, created_by,
                                source_components=None):
        v = self._get_version(version_id)
        v.description = description
        v.notes       = notes
        v.created_by  = created_by
        if source_components is not None:
            v.source_components = source_components
        self._write()

    def update_iteration_metadata(self, version_id, iter_id,
                                  solver_type, analysis_types, description, created_by):
        v = self._get_version(version_id)
        i = self._get_iteration(v, iter_id)
        solver_changed = (i.solver_type != solver_type)
        i.solver_type    = solver_type
        i.analysis_types = analysis_types
        i.description    = description
        i.created_by     = created_by
        if solver_changed:
            i.filename_base = build_filename_base(
                self._log.entity.project, self._log.entity.id,
                version_id, iter_id, solver_type)
        self._write()

    def add_iteration(self, version_id, solver_type, analysis_types,
                      description, created_by):
        v        = self._get_version(version_id)
        existing = [i.id for i in v.iterations]
        iter_id  = next_iteration_id(existing)
        fname    = build_filename_base(self._log.entity.project, self._log.entity.id,
                                       version_id, iter_id, solver_type)
        i = IterationRecord(id=iter_id, description=description, filename_base=fname,
                            created_by=created_by, created_on=_now(),
                            solver_type=solver_type, analysis_types=analysis_types)
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
        run_folder = self._path / RUNS_FOLDER / _run_subfolder(version_id, iter_id, run_id)
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
                        self._path, i.solver_type, i.filename_base, run_id, version_id, iter_id,
                        run.artifacts.output)
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
                        self._path, i.solver_type, i.filename_base, run_id, version_id, iter_id,
                        run.artifacts.output)
                    if run.artifacts.is_production else [])
        self._write(); return warnings

    def update_production_flag(self, version_id, iter_id, run_id, is_production):
        v   = self._get_version(version_id)
        i   = self._get_iteration(v, iter_id)
        run = self._get_run(i, run_id)
        run.artifacts.is_production = is_production
        warnings = (_check_production_artifacts(
                        self._path, i.solver_type, i.filename_base, run_id, version_id, iter_id,
                        run.artifacts.output)
                    if is_production else [])
        self._write(); return warnings

    def add_communication(self, version_id: str, record: CommunicationRecord,
                          version_note: str, iter_notes: dict) -> None:
        """Append a CommunicationRecord and audit notes, then persist."""
        v = self._get_version(version_id)
        v.communications.append(record)
        v.notes.append(version_note)
        for iter_id, note in iter_notes.items():
            i = self._get_iteration(v, iter_id)
            i.notes.append(note)
        self._write()

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
