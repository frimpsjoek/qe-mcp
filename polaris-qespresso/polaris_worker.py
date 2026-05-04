"""
polaris_worker.py - Run once from your Mac to register the worker function.

    python polaris_worker.py

Prints the two UUIDs you need for Claude Desktop config.
"""



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

    Args:
        executable:    QE binary name, e.g. "pw.x", "bands.x", "dos.x"
        input_content: Full text of the .in file
        pseudo_files:  {filename: content} for every pseudopotential needed
        nprocs:        Total MPI ranks (ignored for serial tools)
        nranks_per_node: Ranks per node (Polaris mpiexec --ppn)
        depth:         OMP threads per rank (Polaris mpiexec --depth)
        calc_name:     Stem name for the input file (e.g. "scf", "bands")
        persist_dir:   Absolute or ~-relative path on Polaris where ALL
                       calculation files are stored permanently.
                       Shared across all steps of a workflow (SCF → NSCF
                       → bands.x) so wavefunction files persist between jobs.
        return_files:  List of filenames (relative to persist_dir) whose
                       contents should be returned to the Mac.
                       e.g. ["bands.dat", "bands.dat.gnu"] for bands.x.
                       Wavefunction files in tmp/ are never returned.
    """
    import subprocess
    import time
    import os
    import re
    import glob
    from pathlib import Path

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

    start = time.time()

    # ------------------------------------------------------------------ #
    # Set up the persistent calculation directory on Polaris Lustre        #
    # All files live here: inputs, outputs, wavefunctions (tmp/)           #
    # ------------------------------------------------------------------ #
    d = Path(os.path.expanduser(persist_dir))
    d.mkdir(parents=True, exist_ok=True)

    # Write input file
    inp = d / f"{calc_name}.in"
    inp.write_text(input_content)

    # Pseudopotentials — use pre-staged Polaris path if available,
    # otherwise write from the payload dict (fallback / Docker mode).
    if polaris_pseudo_dir:
        # Point QE directly at the staged directory — no copy needed.
        pseudo_dir = Path(os.path.expanduser(polaris_pseudo_dir))
    else:
        pseudo_dir = d / "pseudo"
        pseudo_dir.mkdir(exist_ok=True)
        for fname, content in pseudo_files.items():
            (pseudo_dir / fname).write_text(content)

    # Build command
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

    env = os.environ.copy()
    existing_ld = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = ld_path + (":" + existing_ld if existing_ld else "")
    env["MPICH_GPU_SUPPORT_ENABLED"] = "0"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,
            cwd=str(d),
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timed out", "returncode": -1,
                "walltime": time.time() - start, "error": "Timeout",
                "persist_dir": str(d), "output_files": {}}
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "returncode": -1,
                "walltime": time.time() - start, "error": str(exc),
                "persist_dir": str(d), "output_files": {}}

    walltime = time.time() - start

    # Write the .out file to the persistent dir too
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

    # ------------------------------------------------------------------ #
    # Return small output files the Mac needs for parsing/plotting.        #
    # Wavefunction files (tmp/) stay on Polaris only.                     #
    # ------------------------------------------------------------------ #
    output_files: dict[str, str] = {}
    for pattern in (return_files or []):
        # Support glob patterns like "pdos*"
        matches = glob.glob(str(d / pattern))
        for match in matches:
            p = Path(match)
            if p.is_file():
                try:
                    output_files[p.name] = p.read_text()
                except Exception:
                    pass  # skip binary files

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "walltime": walltime,
        "error": error,
        "persist_dir": str(d),       # so the Mac knows where files live
        "output_files": output_files,
    }


if __name__ == "__main__":
    from globus_compute_sdk import Client

    gc = Client()

    print("Registering qe_polaris_worker...")
    function_uuid = gc.register_function(qe_polaris_worker)
    print(f"\n  Function UUID: {function_uuid}")

    endpoint_uuid = input("\nPaste your Endpoint UUID: ").strip()

    print("\n--- Add these to your Claude Desktop config env block ---")
    print(f'  "QE_RUNNER": "globus",')
    print(f'  "QE_GLOBUS_ENDPOINT": "{endpoint_uuid}",')
    print(f'  "QE_GLOBUS_FUNCTION": "{function_uuid}"')
    print("---------------------------------------------------------")

    print("\nChecking endpoint status...")
    status = gc.get_endpoint_status(endpoint_uuid)
    print(f"  Status: {status.get('status', 'unknown')}")
