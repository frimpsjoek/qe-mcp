---
name: Geometry Relaxation Skill
description: Smart geometry optimization — auto-selects relax vs vc-relax based on system type, with full structural change report.
arguments:
  - name: structure
    description: Structure file path, formula, or inline coordinates (e.g., 'Cu', 'POSCAR', 'structure.cif')
    required: true
  - name: optimize_cell
    description: Whether to also optimize the unit cell (True = vc-relax, False = relax). Auto-detected if omitted.
    required: false
---
You are running a geometry optimization for **{structure}**.

## Step 1 — Load and validate
- Call `qe_load_structure(structure="{structure}")` and note the number of atoms, species, and whether it is a periodic bulk crystal, a slab/surface, or a molecule.
- Call `qe_validate_structure(structure="{structure}")` and resolve any warnings (overlapping atoms, missing pseudopotentials, insufficient vacuum for molecules/slabs).

## Step 2 — Choose calculation type
Decide based on the loaded structure:

| System type | Tool | Reason |
|-------------|------|--------|
| Bulk crystal | `qe_run_vc_relax` | Cell parameters are free |
| Slab / surface | `qe_run_relax` | Fix cell; only relax atomic positions |
| Molecule in vacuum | `qe_run_relax` | Fixed supercell; relax positions |

Override with `optimize_cell={optimize_cell}` if the user explicitly provided it.

Report which tool you chose and why.

## Step 3 — Launch
Call the chosen tool with `structure="{structure}"` and let smart defaults handle ecutwfc, k-points, and smearing. Note the returned `job_id`.

## Step 4 — Async polling
Call `qe_get_job_status(job_id=<job_id>)` every ~30 seconds. Report ionic step count and max force if available in the status. Continue until `"completed"` or `"failed"`.

## Step 5 — Report results
Provide a structured summary:

- **Initial total energy** (eV)
- **Final total energy** (eV) and energy lowering (ΔE)
- **Number of ionic steps** taken
- **Max residual force** on any atom (eV/Å) — confirm it is below the convergence threshold
- **Cell changes** (vc-relax only): initial vs. final lattice constants (Å) and volume (Å³)
- **Key structural changes**: any bond lengths or angles that changed significantly (> 0.05 Å or > 2°)
- **Suggestion**: if the geometry did not fully converge, recommend re-running from the final structure or adjusting `forc_conv_thr`
