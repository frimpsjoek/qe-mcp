---
name: Band Structure Skill
description: Action-oriented band structure workflow with k-path preview, async job handoff, and electronic structure interpretation.
arguments:
  - name: material
    description: Chemical formula or structure (e.g., 'Si', 'GaAs', 'Fe2O3')
    required: true
  - name: accuracy
    description: "Calculation accuracy: 'low' (ecutwfc=40, 50 k-points), 'medium' (60, 100), or 'high' (80, 150)"
    required: false
---
You are running a complete electronic band structure calculation for **{material}**.

## Step 1 — Pre-flight checks
- Call `qe_list_pseudopotentials` and confirm pseudopotentials exist for every element in `{material}`. If any element is missing, stop and report it.
- Call `qe_validate_structure(structure="{material}")` and confirm no structural issues. Fix any warnings before proceeding.

## Step 2 — Preview the k-path
- Call `qe_get_kpath(structure="{material}")` and show the user the high-symmetry path that will be used (e.g., Γ→X→M→Γ→R for cubic).

## Step 3 — Launch the band structure workflow
Call:
```
qe_workflow_bandstructure(
    structure="{material}",
    ecutwfc={ecutwfc},
    npoints_band={npoints}
)
```
If the runner returns `status="submitted"`, note the returned `job_id` and proceed to Step 4. If the result is immediate, skip to Step 5.

## Step 4 — Async handoff
Do **not** poll repeatedly in the same response. Tell the user the job was submitted, give the `job_id`, and recommend running `uv run qe-watch` in a terminal for notifications. Ask them to request a status check later; then call `qe_get_job_status(job_id=<job_id>)` once and continue to Step 5 only if it is completed.

## Step 5 — Read and interpret results
- Call `qe_read_bands(job_id=<job_id>)` to retrieve the band data.
- Report:
  - **Total energy** (eV)
  - **Fermi energy** (eV)
  - **Band gap** (eV) — if `band_gap_eV` is 0 or absent, classify as **metal**
  - **Gap type** — direct (VBM and CBM at the same k-point) or indirect
  - **Classification** — metal / semiconductor / insulator (gap > ~3 eV)
  - **DFT caveat** — remind the user that GGA/LDA underestimates band gaps by ~30–50% compared to experiment

Consult `qe://llm/materials` for experimental reference values if the material is in the database.

## Step 6 — Plotting code
Output a complete, ready-to-run **Python matplotlib script** (static, saved to PDF). Never use JavaScript, Plotly, Bokeh, or any interactive library. Do not call `plt.show()`. Follow the conventions in `qe://llm/plotting`:
- Figure width: 3.5 in (single column), 300 DPI
- Energy axis centred at the Fermi level (shift bands by −E_Fermi)
- Show E_Fermi as a dashed horizontal line
- Label high-symmetry k-points on the x-axis
- Font: Arial 8 pt, no top/right spines
- Save as PDF for vector output
