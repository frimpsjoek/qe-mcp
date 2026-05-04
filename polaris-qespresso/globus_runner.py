"""
GlobusComputeRunner - Drop-in QERunner that dispatches pw.x to Polaris.

Place this file at: qe_mcp/core/globus_runner.py
"""

import time
from pathlib import Path

from qe_mcp.core.runner import QERunner, RunResult


class GlobusComputeRunner(QERunner):
    """Run QE calculations on Polaris via Globus Compute."""

    def __init__(self, endpoint_uuid: str, function_uuid: str):
        self.endpoint_uuid = endpoint_uuid
        self.function_uuid = function_uuid

    def check_available(self) -> bool:
        try:
            from globus_compute_sdk import Client
            gc = Client()
            status = gc.get_endpoint_status(self.endpoint_uuid)
            return status.get("status") == "online"
        except Exception:
            return False

    def run(
        self,
        executable: str,
        input_file: Path,
        output_file: Path,
        work_dir: Path,
        nprocs: int = 1,
    ) -> RunResult:
        from globus_compute_sdk import Executor

        start = time.time()

        # Read input file and pseudopotentials into memory
        input_content = input_file.read_text()

        pseudo_dir = work_dir / "pseudo"
        pseudo_files: dict[str, str] = {}
        if pseudo_dir.exists():
            for f in pseudo_dir.iterdir():
                if f.is_file():
                    pseudo_files[f.name] = f.read_text()

        # Submit to Polaris
        try:
            with Executor(endpoint_id=self.endpoint_uuid) as gce:
                future = gce.submit_to_registered_function(
                    self.function_uuid,
                    kwargs={
                        "executable": executable,
                        "input_content": input_content,
                        "pseudo_files": pseudo_files,
                        "nprocs": nprocs,
                        "calc_name": input_file.stem,
                    },
                )
                res = future.result(timeout=7200)

        except Exception as exc:
            elapsed = time.time() - start
            return RunResult(
                success=False,
                stdout="",
                stderr=str(exc),
                return_code=-1,
                walltime_seconds=elapsed,
                error_message=f"Globus Compute submission failed: {exc}",
            )

        elapsed = time.time() - start

        # Write output locally so existing tooling still works
        output_path = work_dir / output_file.name
        output_path.write_text(res["stdout"])
        if res.get("stderr"):
            with open(output_path, "a") as f:
                f.write("\n--- STDERR ---\n")
                f.write(res["stderr"])

        error_msg = res.get("error")
        if not error_msg and res["returncode"] != 0:
            error_msg = f"pw.x exited with code {res['returncode']}"

        return RunResult(
            success=res["returncode"] == 0 and error_msg is None,
            stdout=res["stdout"],
            stderr=res.get("stderr", ""),
            return_code=res["returncode"],
            walltime_seconds=res.get("walltime", elapsed),
            output_file=output_path,
            error_message=error_msg,
        )
