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


def get_runner(config: QEConfig) -> QERunner:
    """Get appropriate runner based on config."""
    if config.use_docker:
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
