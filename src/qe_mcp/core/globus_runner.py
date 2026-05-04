"""
GlobusComputeRunner - Dispatches QE calculations to Polaris via Globus Compute.

Storage model:
  - ALL files (inputs, outputs, wavefunctions) live permanently in a
    scratch directory on Polaris's Lustre filesystem.
  - The Mac receives only: stdout + small text output files needed for
    parsing/plotting (bands.dat, dos.dat, pdos_* etc.).
  - Large wavefunction files in tmp/ are never transferred.

Workflow continuity:
  - Every runner call for the same local work_dir uses the SAME remote
    persist_dir, so SCF → NSCF → bands.x all share the directory and
    find each other's wavefunction files.

Async design:
  - run() submits and returns immediately with in_progress=True.
  - collect() is non-blocking: returns in_progress=True if still pending,
    or the full RunResult when done.
  - The caller (calculations.py / job_status.py) decides whether to poll.

Auto-registration:
  - If QE_GLOBUS_FUNCTION is unset, get_or_register_function() registers
    qe_polaris_worker with Globus Compute and caches the UUID at
    ~/.qe_mcp/function_uuid so subsequent MCP restarts skip re-registration.
"""

import contextlib
import io
import logging
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

from qe_mcp.core.runner import QERunner, RunResult

# Silence Globus SDK loggers — they write to stdout/stderr which corrupts
# the MCP JSON-RPC stream over stdio.
for _logger_name in ("globus_compute_sdk", "globus_sdk", "globus_sdk.transport",
                     "globus_sdk.authorizers", "parsl"):
    logging.getLogger(_logger_name).setLevel(logging.CRITICAL)

# Suppress UserWarnings from Globus SDK (e.g. Python version mismatch notices)
warnings.filterwarnings("ignore", category=UserWarning, module="globus_compute_sdk")

_GLOBUS_TIMEOUT = 45  # seconds for any single Globus API call


_gc_client = None


def _globus_client():
    """Return a cached globus_compute_sdk.Client (created once per process)."""
    global _gc_client
    if _gc_client is None:
        from globus_compute_sdk import Client
        with contextlib.redirect_stdout(io.StringIO()):
            _gc_client = Client()
    return _gc_client


def _call_with_timeout(fn, *args, timeout=_GLOBUS_TIMEOUT, **kwargs):
    """Run fn(*args, **kwargs) in a thread; raise TimeoutError if it takes too long."""
    def _silenced():
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*args, **kwargs)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_silenced)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            raise TimeoutError(f"Globus API call timed out after {timeout}s")

_CACHE_DIR = Path.home() / ".qe_mcp"
_FUNCTION_CACHE = _CACHE_DIR / "function_uuid"
_ENDPOINT_CACHE = _CACHE_DIR / "endpoint_uuid"


def get_or_cache_endpoint() -> str | None:
    """Return the Globus endpoint UUID from env var or cache file."""
    from_env = os.environ.get("QE_GLOBUS_ENDPOINT", "").strip()
    if from_env:
        # Write to cache so qe-watch can find it without the env var
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _ENDPOINT_CACHE.write_text(from_env)
        return from_env
    if _ENDPOINT_CACHE.exists():
        cached = _ENDPOINT_CACHE.read_text().strip()
        if cached:
            return cached
    return None

# Small output files each executable should return to the Mac.
# Wavefunction files (tmp/) are never listed — they stay on Polaris.
_RETURN_FILES: dict[str, list[str]] = {
    "pw.x":       [],
    "bands.x":    ["bands.dat.gnu"],
    "dos.x":      [],
    "projwfc.x":  [],
    "pp.x":       [],
    "ph.x":       [],
}


def qe_polaris_worker(
    executable: str,
    input_content: str,
    pseudo_files: dict,
    nprocs: int = 4,
    nranks_per_node: int = 4,
    depth: int = 8,
    calc_name: str = "calc",
    persist_dir: str = "~/.qe_mcp_scratch/default",
    return_files: list | None = None,
    polaris_pseudo_dir: str | None = None,
) -> dict:
    """
    Runs ON Polaris inside a PBS job. Self-contained — no qe_mcp imports.

    Calculation files (input, output, wavefunctions) are stored in
    persist_dir on Polaris's shared Lustre filesystem. They are never
    transferred back except for the small text files listed in return_files
    (e.g. bands.dat, dos.dat) which the Mac needs for parsing/plotting.
    """
    import subprocess
    import time as _time
    import os as _os
    import re
    import glob
    from pathlib import Path as _Path

    QE_BIN = "/soft/applications/quantum_espresso/7.5-nvhpc24.11-libxc700/bin"
    _SERIAL_TOOLS = {"bands.x", "dos.x", "projwfc.x", "pp.x", "ph.x", "dynmat.x"}

    exe_name = executable if executable.endswith(".x") else f"{executable}.x"
    exe = f"{QE_BIN}/{exe_name}"
    is_serial = exe_name in _SERIAL_TOOLS

    ld_path = ":".join([
        "/soft/compilers/nvhpc/Linux_x86_64/24.11/compilers/lib",
        "/soft/compilers/nvhpc/Linux_x86_64/24.11/math_libs/lib64",
        "/soft/compilers/nvhpc/Linux_x86_64/24.11/cuda/lib64",
    ])

    start = _time.time()

    d = _Path(_os.path.expanduser(persist_dir))
    d.mkdir(parents=True, exist_ok=True)

    inp = d / f"{calc_name}.in"
    inp.write_text(input_content)

    if polaris_pseudo_dir:
        pseudo_dir = _Path(_os.path.expanduser(polaris_pseudo_dir))
    else:
        pseudo_dir = d / "pseudo"
        pseudo_dir.mkdir(exist_ok=True)
        for fname, content in pseudo_files.items():
            (pseudo_dir / fname).write_text(content)

    if is_serial:
        cmd = [exe, "-i", str(inp)]
    else:
        cmd = [
            "mpiexec",
            "-n", str(nprocs),
            "--ppn", str(nranks_per_node),
            "--depth", str(depth),
            "--cpu-bind", "depth",
            "--env", f"OMP_NUM_THREADS={depth}",
            "-env", "OMP_PLACES=threads",
            exe,
            "-i", str(inp),
        ]

    env = _os.environ.copy()
    existing_ld = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = ld_path + (":" + existing_ld if existing_ld else "")
    env["MPICH_GPU_SUPPORT_ENABLED"] = "0"

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=7200, cwd=str(d), env=env,
        )
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out", "returncode": -1,
                "walltime": _time.time() - start, "error": "Timeout",
                "persist_dir": str(d), "output_files": {}}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "returncode": -1,
                "walltime": _time.time() - start, "error": str(exc),
                "persist_dir": str(d), "output_files": {}}

    walltime = _time.time() - start

    out_file = d / f"{calc_name}.out"
    out_file.write_text(result.stdout)
    if result.stderr:
        with open(out_file, "a") as f:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)

    error = None
    if result.returncode != 0:
        error = f"{exe_name} exited with code {result.returncode}"
    elif "convergence NOT achieved" in result.stdout:
        error = "SCF convergence not achieved"
    else:
        m = re.search(r"Error in routine\s+\S+.*", result.stdout)
        if m:
            error = m.group(0)

    output_files: dict[str, str] = {}
    for pattern in (return_files or []):
        matches = glob.glob(str(d / pattern))
        for match in matches:
            p = _Path(match)
            if p.is_file():
                try:
                    output_files[p.name] = p.read_text()
                except Exception:
                    pass

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "walltime": walltime,
        "error": error,
        "persist_dir": str(d),
        "output_files": output_files,
    }


def get_or_register_function() -> str:
    """
    Return the Globus Compute function UUID for qe_polaris_worker.

    Checks QE_GLOBUS_FUNCTION env var first, then ~/.qe_mcp/function_uuid.
    If neither is set, registers the function with Globus Compute, caches
    the UUID, and returns it. Registration is silent and automatic.
    """
    # Env var takes highest precedence (explicit config)
    from_env = os.environ.get("QE_GLOBUS_FUNCTION", "").strip()
    if from_env:
        return from_env

    # Check on-disk cache
    if _FUNCTION_CACHE.exists():
        cached = _FUNCTION_CACHE.read_text().strip()
        if cached:
            return cached

    # Auto-register
    try:
        gc = _globus_client()
    except ImportError as exc:
        raise RuntimeError(
            "globus-compute-sdk is not installed. "
            "Run: pip install globus-compute-sdk"
        ) from exc

    function_uuid = _call_with_timeout(gc.register_function, qe_polaris_worker)

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _FUNCTION_CACHE.write_text(function_uuid)

    return function_uuid


class GlobusComputeRunner(QERunner):
    """Run QE calculations on Polaris via Globus Compute."""

    def __init__(self, endpoint_uuid: str, function_uuid: str):
        self.endpoint_uuid = endpoint_uuid
        self.function_uuid = function_uuid
        self._persist_dirs: dict[str, str] = {}
        self._scratch_root = os.environ.get("QE_POLARIS_SCRATCH", "~/.qe_mcp_scratch")
        self._polaris_pseudo = os.environ.get("QE_POLARIS_PSEUDO", "")

    def check_available(self) -> bool:
        try:
            gc = _globus_client()
            status = _call_with_timeout(gc.get_endpoint_status, self.endpoint_uuid, timeout=15)
            return status.get("status") == "online"
        except Exception:
            return False

    def _get_persist_dir(self, work_dir: Path) -> str:
        key = str(work_dir.resolve())
        if key not in self._persist_dirs:
            self._persist_dirs[key] = f"{self._scratch_root}/{work_dir.name}"
        return self._persist_dirs[key]

    def _build_payload(
        self,
        executable: str,
        input_file: Path,
        work_dir: Path,
        nprocs: int,
    ) -> dict:
        """Build the keyword arguments dict for gc.run()."""
        input_content = input_file.read_text()

        pseudo_files: dict[str, str] = {}
        if not self._polaris_pseudo:
            pseudo_dir = work_dir / "pseudo"
            if pseudo_dir.exists():
                for f in pseudo_dir.iterdir():
                    if f.is_file():
                        pseudo_files[f.name] = f.read_text()

        persist_dir = self._get_persist_dir(work_dir)
        exe_name = executable if executable.endswith(".x") else f"{executable}.x"
        return_files = _RETURN_FILES.get(exe_name, [])

        return {
            "executable": executable,
            "input_content": input_content,
            "pseudo_files": pseudo_files,
            "nprocs": nprocs,
            "calc_name": input_file.stem,
            "persist_dir": persist_dir,
            "return_files": return_files,
            "polaris_pseudo_dir": self._polaris_pseudo or None,
        }

    def _submit(
        self,
        executable: str,
        input_file: Path,
        work_dir: Path,
        nprocs: int = 1,
    ) -> str:
        """Submit to Globus Compute and return task_id immediately."""
        gc = _globus_client()
        payload = self._build_payload(executable, input_file, work_dir, nprocs)
        task_id = _call_with_timeout(
            gc.run,
            endpoint_id=self.endpoint_uuid,
            function_id=self.function_uuid,
            **payload,
        )
        return str(task_id)

    def run(
        self,
        executable: str,
        input_file: Path,
        output_file: Path,
        work_dir: Path,
        nprocs: int = 1,
    ) -> RunResult:
        """Submit to Globus Compute and return immediately (non-blocking)."""
        start = time.time()
        try:
            task_id = self._submit(executable, input_file, work_dir, nprocs)
        except Exception as exc:
            return RunResult(
                success=False,
                stdout="",
                stderr=str(exc),
                return_code=-1,
                walltime_seconds=time.time() - start,
                error_message=f"Globus submission failed: {exc}",
            )
        return RunResult(
            success=False,
            stdout="",
            stderr="",
            return_code=-1,
            walltime_seconds=time.time() - start,
            in_progress=True,
            task_id=task_id,
        )

    def collect(
        self,
        task_id: str,
        work_dir: Path,
        output_filename: str,
    ) -> RunResult:
        """
        Non-blocking result check.

        Returns a RunResult with in_progress=True if the job is still running,
        or a completed RunResult (success or failure) when done.
        Uses get_task() for clean status inspection rather than exception parsing.
        """
        try:
            gc = _globus_client()
            task = _call_with_timeout(gc.get_task, task_id)
        except TimeoutError as exc:
            return RunResult(
                success=False,
                stdout="",
                stderr=str(exc),
                return_code=-1,
                walltime_seconds=0.0,
                error_message=str(exc),
                in_progress=True,  # Treat timeout as still-pending, not failed
            )
        except Exception as exc:
            return RunResult(
                success=False,
                stdout="",
                stderr=str(exc),
                return_code=-1,
                walltime_seconds=0.0,
                error_message=f"Globus error: {exc}",
            )

        status = task.get("status", "").lower()
        _IN_PROGRESS = ("pending", "waiting-for-ep", "waiting-for-nodes", "running", "task-transition")
        if status in _IN_PROGRESS:
            return RunResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                walltime_seconds=0.0,
                in_progress=True,
                task_id=task_id,
                globus_status=status,
            )

        # Terminal state — fetch the actual result payload
        try:
            res = gc.get_result(task_id)
        except Exception as exc:
            return RunResult(
                success=False,
                stdout="",
                stderr=str(exc),
                return_code=-1,
                walltime_seconds=0.0,
                error_message=f"Globus result error: {exc}",
            )

        # Write stdout to local .out file so existing parsers work
        output_path = work_dir / output_filename
        output_path.write_text(res["stdout"])
        if res.get("stderr"):
            with open(output_path, "a") as fh:
                fh.write("\n--- STDERR ---\n")
                fh.write(res["stderr"])

        # Write any returned output files (bands.dat.gnu, etc.)
        for fname, content in res.get("output_files", {}).items():
            (work_dir / fname).write_text(content)

        error_msg = res.get("error")
        if not error_msg and res["returncode"] != 0:
            error_msg = f"{output_filename}: exited with code {res['returncode']}"

        return RunResult(
            success=res["returncode"] == 0 and error_msg is None,
            stdout=res["stdout"],
            stderr=res.get("stderr", ""),
            return_code=res["returncode"],
            walltime_seconds=res.get("walltime", 0.0),
            output_file=output_path,
            error_message=error_msg,
        )
