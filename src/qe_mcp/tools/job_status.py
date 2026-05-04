"""
get_job_status: poll an async QE job and advance workflow state machines.

For single-step calculations (scf, relax, vc-relax): tries to collect the
Globus result, parses it, and returns the same dict as the synchronous tool.

For multi-step workflows (bandstructure, dos, relax_scf): checks the current
step's result, submits the next step if done, and returns when fully complete.
"""

import json
import os
from pathlib import Path
from typing import Any

from qe_mcp.config import QEConfig
from qe_mcp.core.job_registry import JobRegistry
from qe_mcp.core.parser import QEOutputParser


def get_job_status(job_id: str) -> dict[str, Any]:
    """
    Check the status of a previously submitted async job.

    Args:
        job_id: The job ID returned when the calculation was submitted
                (e.g. 'scf_a1b2c3d4' or 'bands_xyz12345').

    Returns:
        Dict with 'status' key:
          - 'pending'   — job is still running; try again in a few minutes
          - 'advancing' — workflow step completed, next step submitted
          - 'completed' — job finished; result fields included
          - 'failed'    — job failed; 'error' field included
    """
    config = QEConfig.from_environment()
    registry = JobRegistry(config.workdir)
    record = registry.get(job_id)

    if record is None:
        return {
            "success": False,
            "error": f"Job '{job_id}' not found in registry at {config.workdir}.",
        }

    if record["status"] == "completed":
        return {"status": "completed", "job_id": job_id, **(record["result"] or {})}

    if record["status"] == "failed":
        return {"status": "failed", "job_id": job_id, "error": record.get("error")}

    # Job is "submitted" — create a Globus runner (no availability check needed
    # for gc.get_result, which queries the Globus service, not the endpoint)
    work_dir = Path(record["work_dir"])
    runner_instance = _get_globus_runner()

    if runner_instance is None:
        return {
            "success": False,
            "error": "QE_GLOBUS_ENDPOINT or QE_GLOBUS_FUNCTION not set. "
                     "Cannot poll job status.",
        }

    # Check if it's a workflow (has manifest.json)
    manifest_path = work_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        from qe_mcp.tools.workflows import advance_workflow
        result = advance_workflow(work_dir, manifest, runner_instance)

        if result.get("status") == "completed":
            registry.update(job_id, status="completed", result=result)
        elif result.get("status") == "failed":
            registry.update(job_id, status="failed", error=result.get("error"))
        elif result.get("status") == "advancing":
            # Update task_id in registry so next poll uses the new task
            new_task_id = manifest.get("task_id")
            if new_task_id:
                registry.update(job_id, task_id=new_task_id)
        return result

    # Single-step calculation
    calc_type = record["calc_type"]
    task_id = record["task_id"]
    output_filename = _output_filename(calc_type, job_id)

    result = runner_instance.collect(task_id, work_dir, output_filename)

    if result.in_progress:
        gs = result.globus_status or "pending"
        if gs == "running":
            message = "Job is actively computing on Polaris nodes. Check back in ~5 minutes."
        else:
            message = "Job is waiting in the Polaris PBS queue. Could take minutes to hours depending on cluster load."
        return {
            "status": "pending",
            "job_id": job_id,
            "calc_type": calc_type,
            "queue_status": gs,
            "message": message,
        }

    if not result.success:
        registry.update(job_id, status="failed", error=result.error_message)
        return {"status": "failed", "job_id": job_id, "error": result.error_message}

    parsed = _parse_single_result(calc_type, result, work_dir, job_id)
    registry.update(job_id, status="completed", result=parsed)
    return {"status": "completed", "job_id": job_id, **parsed}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_globus_runner():
    """Instantiate GlobusComputeRunner using env vars or cached UUIDs."""
    from qe_mcp.core.globus_runner import GlobusComputeRunner, get_or_register_function, get_or_cache_endpoint
    endpoint = get_or_cache_endpoint()
    if not endpoint:
        return None
    try:
        function = get_or_register_function()
    except Exception:
        return None
    return GlobusComputeRunner(endpoint_uuid=endpoint, function_uuid=function)


def _output_filename(calc_type: str, job_id: str) -> str:
    return f"{job_id}.out"


def _parse_single_result(
    calc_type: str, result, work_dir: Path, job_id: str
) -> dict[str, Any]:
    parsed = QEOutputParser.parse_scf(result.stdout)
    base = {
        "success": result.success,
        "total_energy_eV": parsed.total_energy_ev,
        "total_energy_Ry": parsed.total_energy_ry,
        "fermi_energy_eV": parsed.fermi_energy_ev,
        "converged": parsed.converged,
        "forces_eV_per_angstrom": parsed.forces,
        "n_iterations": parsed.n_iterations,
        "total_magnetization": parsed.total_magnetization,
        "walltime_seconds": result.walltime_seconds,
        "output_dir": str(work_dir),
        "output_file": str(work_dir / f"{job_id}.out"),
    }
    if calc_type in ("relax", "vc-relax"):
        base["relaxation_converged"] = "End of BFGS Geometry Optimization" in result.stdout
    return base
