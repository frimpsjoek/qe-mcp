"""
End-to-end smoke test: submit a minimal Si SCF calculation to Polaris
via GlobusComputeRunner and verify the full pipeline.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load secrets from this repo's .env. Passing the path explicitly avoids
# python-dotenv's frame inspection path when this script is launched oddly.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Set required environment paths if not loaded via .env
os.environ.setdefault("QE_RUNNER", "globus")
os.environ.setdefault("QE_POLARIS_SCRATCH", "~/.qe_mcp_scratch")
os.environ.setdefault("QE_POLARIS_PSEUDO", "")
os.environ.setdefault("QE_PSEUDO_DIR", "/Users/frimpsjoe/QE_MCP/pseudopotentials/sg15_oncv")
os.environ.setdefault("QE_WORKDIR", "/Users/frimpsjoe/QE_MCP/qe_calculations")

sys.path.insert(0, "/Users/frimpsjoe/QE_MCP/src")

from qe_mcp.core.globus_runner import GlobusComputeRunner

# ── Setup ─────────────────────────────────────────────────────────────────────

runner = GlobusComputeRunner(
    endpoint_uuid=os.environ["QE_GLOBUS_ENDPOINT"],
    function_uuid=os.environ["QE_GLOBUS_FUNCTION"],
)

# Check endpoint is alive
print("1. Checking endpoint status...")
available = runner.check_available()
print(f"   Endpoint online: {available}")
if not available:
    print("   ERROR: Endpoint not online. Is globus-compute-endpoint running on Polaris?")
    sys.exit(1)

# ── Create test calculation ───────────────────────────────────────────────────

work_dir = Path("/Users/frimpsjoe/QE_MCP/qe_calculations/test_globus_e2e")
work_dir.mkdir(parents=True, exist_ok=True)

# Minimal Si SCF input — very low cutoff and k-points for speed
input_text = """\
&CONTROL
  calculation = 'scf'
  outdir = './tmp'
  pseudo_dir = './pseudo'
  prefix = 'si'
  tprnfor = .true.
  tstress = .true.
/
&SYSTEM
  ibrav = 2
  celldm(1) = 10.2
  nat = 2
  ntyp = 1
  ecutwfc = 20.0
/
&ELECTRONS
  mixing_beta = 0.7
  conv_thr = 1.0d-6
/
ATOMIC_SPECIES
  Si 28.085 Si_ONCV_PBE-1.2.upf
ATOMIC_POSITIONS crystal
  Si 0.00 0.00 0.00
  Si 0.25 0.25 0.25
K_POINTS automatic
  2 2 2 0 0 0
"""

input_file = work_dir / "scf.in"
input_file.write_text(input_text)

output_file = work_dir / "scf.out"

# Copy pseudopotential
pseudo_dir = work_dir / "pseudo"
pseudo_dir.mkdir(exist_ok=True)

src_pseudo = Path(os.environ["QE_PSEUDO_DIR"])
pseudo_candidates = list(src_pseudo.glob("Si_ONCV_PBE*")) + list(src_pseudo.glob("Si*"))
if pseudo_candidates:
    import shutil
    for p in pseudo_candidates[:1]:
        shutil.copy2(p, pseudo_dir / "Si_ONCV_PBE-1.2.upf")
        print(f"2. Using pseudo: {p.name}")
else:
    print("   ERROR: No Si pseudopotential found!")
    sys.exit(1)

# ── Submit ────────────────────────────────────────────────────────────────────

print(f"3. Submitting SCF to Polaris...")
print(f"   work_dir: {work_dir}")
print(f"   persist_dir will be: ~/.qe_mcp_scratch/test_globus_e2e")
t0 = time.time()

result = runner.run(
    executable="pw.x",
    input_file=input_file,
    output_file=output_file,
    work_dir=work_dir,
    nprocs=4,
)

if result.in_progress and result.task_id:
    print(f"   submitted task: {result.task_id}")
    deadline = time.time() + int(os.environ.get("QE_E2E_TIMEOUT_SECONDS", "900"))
    while time.time() < deadline:
        result = runner.collect(
            task_id=result.task_id,
            work_dir=work_dir,
            output_filename=output_file.name,
        )
        if not result.in_progress:
            break
        status = result.globus_status or "pending"
        print(f"   task status: {status}; checking again in 15s")
        time.sleep(15)
    else:
        result.success = False
        result.error_message = "Timed out waiting for Globus task"

elapsed = time.time() - t0

# ── Report ────────────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print(f"RESULT")
print(f"{'='*60}")
print(f"  success:      {result.success}")
print(f"  return_code:  {result.return_code}")
print(f"  walltime:     {result.walltime_seconds:.1f}s (total roundtrip: {elapsed:.1f}s)")
print(f"  error:        {result.error_message}")
print(f"  output_file:  {result.output_file}")

if result.success:
    # Parse total energy from stdout
    for line in result.stdout.splitlines():
        if "!" in line and "total energy" in line:
            print(f"  ENERGY:       {line.strip()}")
        if "total   stress" in line:
            print(f"  STRESS:       (present)")
        if "Total force" in line:
            print(f"  FORCES:       {line.strip()}")
    print(f"\n✅ END-TO-END TEST PASSED")
    sys.exit(0)
else:
    print(f"\n❌ TEST FAILED")
    # Show last 30 lines of stderr/stdout for debugging
    if result.stderr:
        print("\n--- STDERR (last 30 lines) ---")
        for line in result.stderr.strip().splitlines()[-30:]:
            print(f"  {line}")
    if result.stdout:
        print("\n--- STDOUT (last 30 lines) ---")
        for line in result.stdout.strip().splitlines()[-30:]:
            print(f"  {line}")
    sys.exit(1)
