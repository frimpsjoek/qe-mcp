---
name: Calculation Report Skill
description: Generate a comprehensive human-readable analysis report for a completed QE workflow, including parameters, results, interpretation, and next steps.
arguments:
  - name: job_id
    description: Job ID of the completed calculation to report on
    required: true
---
You are generating a full analysis report for job **{job_id}**.

## Step 1 — Retrieve job metadata
Call `qe_get_job_status(job_id="{job_id}")` and note: calculation type, material, status, working directory, and runner type.

## Step 2 — Inventory output files
Call `qe_list_files(job_id="{job_id}")` and list all available files (input, output, save directory, data files).

## Step 3 — Read all results
Read every available output type:
- Total energy / SCF output (from the `.out` file if accessible)
- Band data: `qe_read_bands` if a `.gnu` file exists
- DOS data: `qe_read_dos` and `qe_read_pdos` if `.dat` / `.pdos_*` files exist

## Step 4 — Write the report

Structure the report as follows:

---

### Calculation Report: {job_id}

**Material:** [name]  
**Calculation type:** [SCF / Band structure / DOS / Relax / etc.]  
**Runner:** [Docker / Globus HPC]  
**Status:** [Completed / Failed]  

#### Computational Parameters
| Parameter | Value |
|-----------|-------|
| ecutwfc   | X Ry  |
| ecutrho   | X Ry  |
| kpoints   | ...   |
| smearing  | ...   |
| spin_polarized | Yes/No |

#### Key Results
| Quantity | Value |
|----------|-------|
| Total energy | X eV (Y Ry) |
| Fermi energy | X eV |
| Band gap (DFT) | X eV (direct/indirect) |
| Magnetic moment | X μB/cell |
| Max force (relax) | X eV/Å |

#### Physical Interpretation
[2–4 sentences: classify the material (metal/semiconductor/insulator/magnetic), report the most significant result, compare with known experimental values from `qe://llm/materials` if available]

#### DFT Limitations and Caveats
[Note any known limitations for this specific material/property:
- Band gaps underestimated by GGA (~30–50%)
- Magnetic moments in itinerant magnets usually accurate; correlated oxides may need DFT+U
- Van der Waals not captured without dispersion corrections
- Cell volume typically overestimated ~1–3% by GGA]

#### Suggested Next Steps
[List 2–3 logical follow-up calculations, e.g.:
- Run `skill_band_structure` if only SCF was done
- Run `skill_magnetic` if magnetic elements are present
- Run `skill_converge` to validate parameters
- Use `skill_plot` to generate publication figures]

---
