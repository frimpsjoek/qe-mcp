---
name: DOS Skill
description: Action-oriented DOS + PDOS workflow with spin detection, async job handoff, and orbital/magnetic interpretation.
arguments:
  - name: material
    description: Chemical formula or structure (e.g., 'Cu', 'Fe', 'TiO2')
    required: true
  - name: spin_polarized
    description: Enable spin polarization (auto-detected for magnetic elements if omitted)
    required: false
---
You are running a complete density-of-states (DOS + PDOS) calculation for **{material}**.

## Step 1 — Auto-detect spin polarization
Inspect the elements in `{material}`. If it contains any of Fe, Co, Ni, Mn, Cr, V, Gd, Eu, Tb, Dy, Ho, Er, set `spin_polarized=True` automatically (unless the user explicitly set it to False). Report your decision.

## Step 2 — Launch the DOS workflow
Call:
```
qe_workflow_dos(
    structure="{material}",
    spin_polarized=<detected or {spin_polarized}>,
    kpoints_nscf=[12, 12, 12]
)
```
If async, note the returned `job_id` and proceed to Step 3.

## Step 3 — Async handoff
Do **not** poll repeatedly in the same response. Tell the user the job was submitted, give the `job_id`, and recommend running `uv run qe-watch` for notifications. Ask them to request a status check later; then call `qe_get_job_status(job_id=<job_id>)` once and continue to Step 4 only if it is completed.

## Step 4 — Read results
- Call `qe_read_dos(job_id=<job_id>)` for the total DOS
- Call `qe_read_pdos(job_id=<job_id>)` for projected/orbital DOS

## Step 5 — Interpret
Provide physical interpretation tailored to the material type:

**For metals:**
- Locate the d-band centre (energy of centre of mass of d-DOS relative to E_Fermi) — relevant for catalytic activity (Hammer–Nørskov model)
- Identify whether the material is a good or poor conductor based on DOS at E_Fermi

**For semiconductors/insulators:**
- Identify the gap region in the DOS
- Assign orbital character to valence and conduction band edges (from PDOS)

**For magnetic materials (spin_polarized=True):**
- Report exchange splitting (Δ = E_↓ − E_↑ of majority/minority band centres)
- Report net spin moment from integrated spin-up minus spin-down DOS
- Compare with `qe://llm/materials` experimental reference if available

## Step 6 — Plotting code
Output a complete, ready-to-run **Python matplotlib script** (static, saved to PDF). Never use JavaScript, Plotly, Bokeh, or any interactive library. Do not call `plt.show()`. Follow `qe://llm/plotting`:
- DOS orientation: energy on x-axis, DOS on y-axis
- Apply 0.03 eV Gaussian broadening
- Vertical dashed line at E_Fermi (shift energy axis so E_Fermi = 0)
- Energy window: −5 to +5 eV
- For PDOS: one line per orbital (s, p, d) with distinct muted colours
- For spin-polarized: spin-up positive, spin-down negative (mirror plot)
- Figure width: 3.5 in, 300 DPI, no top/right spines, save as PDF
