import argparse
import subprocess
import sys
import time

from qe_mcp.config import QEConfig
from qe_mcp.core.job_registry import JobRegistry
from qe_mcp.tools.job_status import get_job_status


def _notify(title: str, body: str) -> None:
    subprocess.run(
        ["osascript", "-e", f'display notification "{body}" with title "{title}" sound name "Glass"'],
        check=False, capture_output=True,
    )


def _warm_up_globus() -> None:
    """Initialize the Globus client eagerly so the first poll isn't slow."""
    try:
        from qe_mcp.core.globus_runner import _globus_client
        _globus_client()
    except Exception:
        pass


def watch(poll_interval: int = 10) -> None:
    config = QEConfig.from_environment()
    registry = JobRegistry(config.workdir)
    print(f"qe-watch: monitoring {config.workdir} every {poll_interval}s  (Ctrl-C to stop)")
    _warm_up_globus()

    notified: set[str] = set()

    while True:
        try:
            for job in registry.list_jobs(status="submitted"):
                job_id = job["job_id"]
                if job_id in notified:
                    continue

                result = get_job_status(job_id)
                status = result.get("status")

                if status == "completed":
                    notified.add(job_id)
                    _notify("QE Job Complete ✓", f"{job_id} ({job.get('calc_type', '')}) finished")
                    print(f"[done] {job_id}")

                elif status == "failed":
                    notified.add(job_id)
                    error = str(result.get("error", "unknown"))[:80]
                    _notify("QE Job Failed ✗", f"{job_id}: {error}")
                    print(f"[fail] {job_id}: {error}")

                elif status == "advancing":
                    print(f"[step] {job_id} advancing to next step")

        except KeyboardInterrupt:
            print("\nqe-watch stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"[error] {e}", file=sys.stderr)

        time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch QE jobs and send macOS notifications")
    parser.add_argument("--interval", type=int, default=10, help="Poll interval in seconds (default 10)")
    args = parser.parse_args()
    watch(poll_interval=args.interval)
