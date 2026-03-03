from schema import SolverType, SCHEMA_VERSION

APP_TITLE:          str = "FEA Trace"
APP_VERSION:        str = "2.0.0"
DEVELOPER_NAME:     str = "Pedro Ferreira"
DEVELOPER_EMAIL:    str = "pedro.cferreira@ceiia.com"
WINDOW_SIZE:  str = "1280x800"
WINDOW_MIN_W: int = 900
WINDOW_MIN_H: int = 600

LOCK_TIMEOUT_SECONDS: int = 30
LOCK_FILENAME:        str = "version_log.yaml.lock"
LOG_FILENAME:         str = "version_log.yaml"

REQUIRED_PRODUCTION_ARTIFACTS: dict[SolverType, list[str]] = {
    SolverType.IMPLICIT: [".fem", ".h3d"],
    SolverType.EXPLICIT: [".rad", ".h3d",".T01"],
    SolverType.MBD:      [".xml", ".h3d"],
}

MODELS_FOLDER:          str = "02_Models"
RUNS_FOLDER:            str = "03_Runs"
RESULTS_FOLDER:         str = "04_Results"
COMMUNICATIONS_FOLDER:  str = "05_Communications"
TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"
SIDEBAR_WIDTH:  int = 240
ENTITY_ID_MAX_LEN: int = 12
