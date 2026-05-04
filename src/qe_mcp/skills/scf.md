---
name: SCF Skill
description: Quick single-point self-consistent field energy calculation with automatic parameter selection and result summary.
arguments:
  - name: material
    description: Chemical formula or structure (e.g., 'Si', 'Cu', 'Fe2O3')
    required: true
---
You are running a single-point SCF calculation for **{material}**.

## Step 1 — Launch SCF
Call `qe_run_scf(structure="{material}")`. Smart defaults will handle:
- `ecutwfc` (from pseudopotential recommendations)
- `ecutrho` (4× ecutwfc for norm-conserving SG15 PPs)
- `kpoints` (auto-scaled to cell size)
- `smearing` (cold/Marzari-Vanderbilt for metals; gaussian for insulators)
- `spin_polarized` (auto-enabled for Fe, Co, Ni, Mn, Cr, V, Gd, Eu, Tb, Dy, Ho, Er)

Note the returned `job_id`.

## Step 2 — Async handoff
If the job is submitted asynchronously, do **not** poll repeatedly in the same response. Tell the user the job was submitted, give the `job_id`, and recommend running `uv run qe-watch` for notifications. Ask them to request a status check later; then call `qe_get_job_status(job_id=<job_id>)` once and continue to Step 3 only if it is completed.

## Step 3 — Report results
- **Total energy**: report in both Ry and eV
- **Fermi energy** (eV)
- **Convergence**: confirm the SCF converged (number of iterations)
- **Magnetization** (μB per unit cell) if spin-polarized
- **Suggested next step**: if the user wants more, suggest band structure (`skill_band_structure`) or DOS (`skill_dos`)
