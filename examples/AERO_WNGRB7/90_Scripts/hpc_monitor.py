"""
hpc_monitor.py — Simple utility to monitor HPC cluster job status.

Usage:
    python hpc_monitor.py <job_id>
    python hpc_monitor.py --list

Polls the cluster queue every 30 seconds and prints a status update.
Sends a desktop notification when the job completes or fails.

Note: This is a placeholder script for the FEA Trace Examples dataset.
      Replace the cluster commands below with your site-specific scheduler
      (SLURM: sacct / squeue, PBS: qstat, LSF: bjobs).
"""

import sys
import time
import subprocess
from datetime import datetime

POLL_INTERVAL_S = 30
SCHEDULER       = "slurm"   # "slurm" | "pbs" | "lsf"


def get_job_status_slurm(job_id: str) -> dict:
    """Return {'state': str, 'elapsed': str, 'reason': str} via sacct."""
    try:
        result = subprocess.run(
            ["sacct", "-j", job_id, "--format=State,Elapsed,Reason", "--noheader", "-X"],
            capture_output=True, text=True, timeout=10,
        )
        parts = result.stdout.strip().split()
        return {
            "state":   parts[0] if len(parts) > 0 else "UNKNOWN",
            "elapsed": parts[1] if len(parts) > 1 else "-",
            "reason":  parts[2] if len(parts) > 2 else "-",
        }
    except Exception as exc:
        return {"state": "ERROR", "elapsed": "-", "reason": str(exc)}


def monitor(job_id: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] Monitoring job {job_id} (poll every {POLL_INTERVAL_S}s)...")
    terminal_states = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}
    while True:
        info = get_job_status_slurm(job_id)
        state   = info["state"]
        elapsed = info["elapsed"]
        print(f"  [{datetime.now():%H:%M:%S}]  State: {state:<20}  Elapsed: {elapsed}")
        if state in terminal_states:
            print(f"\nJob {job_id} finished with state: {state}")
            break
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    monitor(sys.argv[1])
