"""
QE Calculation Runner - Docker and Local execution.

Handles running Quantum ESPRESSO calculations via Docker or local executables.
"""

import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Literal

from qe_mcp.config import QEConfig


@dataclass
class RunResult:
    """Result of a QE calculation run."""

    success: bool
    stdout: str
    stderr: str
    return_code: int
    walltime_seconds: float
    output_file: Path | None = None
    error_message: str | None = None
    in_progress: bool = False      # True when submitted async, not yet complete
    task_id: str | None = None     # Remote task ID (Globus, etc.)
    globus_status: str | None = None  # Globus task state: pending/running/success/failed


class QERunner(ABC):
    """Abstract base class for QE runners."""

    @abstractmethod
    def run(
        self,
        executable: str,
        input_file: Path,
        output_file: Path,
        work_dir: Path,
        nprocs: int = 1,
    ) -> RunResult:
        """Run a QE executable."""
        pass

    @abstractmethod
    def check_available(self) -> bool:
        """Check if the runner is available."""
        pass


class DockerQERunner(QERunner):
    """Run QE calculations via Docker."""

    def __init__(self, image: str = "qe-local"):
        self.image = image

    def check_available(self) -> bool:
        """Check if Docker and the QE image are available."""
        try:
            # Check Docker is running
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                return False

            # Check image exists
            result = subprocess.run(
                ["docker", "image", "inspect", self.image],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def run(
        self,
        executable: str,
        input_file: Path,
        output_file: Path,
        work_dir: Path,
        nprocs: int = 1,
    ) -> RunResult:
        """
        Run a QE executable via Docker.

        Args:
            executable: Name of executable (e.g., "pw.x", "bands.x")
            input_file: Path to input file (relative to work_dir)
            output_file: Path to output file (relative to work_dir)
            work_dir: Working directory containing input files
            nprocs: Number of MPI processes
        """
        import time

        start_time = time.time()

        # Build Docker command
        # Mount work_dir to /work in container
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{work_dir.absolute()}:/work",
            "-w",
            "/work",
            self.image,
        ]

        # Add MPI if nprocs > 1
        if nprocs > 1:
            cmd.extend(["mpirun", "-np", str(nprocs), "--allow-run-as-root"])

        cmd.extend([executable, "-i", input_file.name])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                cwd=work_dir,
            )

            walltime = time.time() - start_time

            # Write output to file
            output_path = work_dir / output_file.name
            with open(output_path, "w") as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write("\n--- STDERR ---\n")
                    f.write(result.stderr)

            # Check for QE errors in output
            error_msg = None
            if "Error" in result.stdout or result.returncode != 0:
                error_msg = self._extract_error(result.stdout)

            return RunResult(
                success=result.returncode == 0 and error_msg is None,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                walltime_seconds=walltime,
                output_file=output_path,
                error_message=error_msg,
            )

        except subprocess.TimeoutExpired:
            return RunResult(
                success=False,
                stdout="",
                stderr="Calculation timed out after 1 hour",
                return_code=-1,
                walltime_seconds=3600,
                error_message="Timeout",
            )
        except Exception as e:
            return RunResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                walltime_seconds=time.time() - start_time,
                error_message=str(e),
            )

    def _extract_error(self, output: str) -> str | None:
        """Extract error message from QE output."""
        import re

        # Look for common QE error patterns
        patterns = [
            r"Error in routine\s+(\S+)\s+\((\d+)\):\s*\n\s*(.+)",
            r"%%%+\s*\n\s*Error[^\n]*\n\s*(.+?)\s*\n\s*%%%+",
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.MULTILINE)
            if match:
                return match.group(0)

        if "convergence NOT achieved" in output:
            return "SCF convergence not achieved"

        return None


class LocalQERunner(QERunner):
    """Run QE calculations using local executables."""

    def __init__(self, config: QEConfig):
        self.config = config

    def check_available(self) -> bool:
        """Check if local QE executables are available."""
        pw_path = self.config.get_executable_path("pw")
        return shutil.which(pw_path) is not None

    def run(
        self,
        executable: str,
        input_file: Path,
        output_file: Path,
        work_dir: Path,
        nprocs: int = 1,
    ) -> RunResult:
        """Run a QE executable locally."""
        import time

        start_time = time.time()

        # Get executable path
        exe_path = self.config.get_executable_path(executable.replace(".x", ""))

        # Build command
        cmd = []
        if nprocs > 1:
            cmd.extend(["mpirun", "-np", str(nprocs)])
        cmd.extend([exe_path, "-i", str(input_file)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                cwd=work_dir,
            )

            walltime = time.time() - start_time

            # Write output to file
            output_path = work_dir / output_file.name
            with open(output_path, "w") as f:
                f.write(result.stdout)

            return RunResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                walltime_seconds=walltime,
                output_file=output_path,
            )

        except subprocess.TimeoutExpired:
            return RunResult(
                success=False,
                stdout="",
                stderr="Timeout",
                return_code=-1,
                walltime_seconds=3600,
                error_message="Calculation timed out",
            )
        except Exception as e:
            return RunResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                walltime_seconds=time.time() - start_time,
                error_message=str(e),
            )


def get_runner(config: QEConfig, runner_type: str | None = None) -> QERunner:
    """Get appropriate runner based on runner_type override or QE_RUNNER environment variable."""
    import os

    if not runner_type:
        runner_type = os.environ.get("QE_RUNNER", "docker" if config.use_docker else "local")

    # Normalize aliases
    if runner_type in ("polaris", "hpc"):
        runner_type = "globus"

    if runner_type == "globus":
        endpoint = os.environ.get("QE_GLOBUS_ENDPOINT", "").strip()
        if not endpoint:
            raise RuntimeError(
                "QE_RUNNER=globus requires QE_GLOBUS_ENDPOINT to be set. "
                "Find it by running: globus-compute-endpoint list  (on Polaris)"
            )
        from qe_mcp.core.globus_runner import GlobusComputeRunner, get_or_register_function
        function = get_or_register_function()
        runner = GlobusComputeRunner(endpoint_uuid=endpoint, function_uuid=function)
        if not runner.check_available():
            raise RuntimeError(
                f"Globus Compute endpoint {endpoint} is not online. "
                "SSH to Polaris and run: globus-compute-endpoint start qe-polaris-1"
            )
        return runner

    elif runner_type == "docker" or config.use_docker:
        runner = DockerQERunner(config.docker_image)
        if runner.check_available():
            return runner
        raise RuntimeError(
            f"Docker runner requested but image '{config.docker_image}' not available. "
            "Build it with: docker build -t qe-local ."
        )

    else:
        runner = LocalQERunner(config)
        if runner.check_available():
            return runner
        raise RuntimeError(
            "Local QE executables not found. "
            "Set QE_PREFIX environment variable or use Docker mode."
        )
