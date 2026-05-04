---
name: Structure Comparison Skill
description: Rank multiple structures by thermodynamic stability using consistent DFT total energies per atom.
arguments:
  - name: structures
    description: Comma-separated list of structures/formulas to compare (e.g., 'diamond, graphite, C60')
    required: true
---
You are comparing the thermodynamic stability of: **{structures}**

## Step 1 — Parse structures
Split `{structures}` by commas to get the list of materials. Load each with `qe_load_structure` and note the number of atoms per formula unit (needed to compute energy per atom).

## Step 2 — Consistent SCF calculations
Run `qe_run_scf` on each structure using **identical parameters**:
- `ecutwfc = 60 Ry` (or the highest recommended value among all elements present)
- `kpoints` appropriate for each cell size (use `qe_suggest_kpoints` for each structure)
- Same `smearing` type and `degauss`

Launch the SCF jobs. If any are submitted asynchronously, do **not** poll repeatedly in the same response. Return the submitted `job_id` values, recommend `uv run qe-watch`, and ask the user to request a later status check. Continue only when all jobs are completed.

## Step 3 — Build comparison table
| Structure | E_total (eV) | N atoms | E/atom (eV) | Volume/atom (Å³) | Density (g/cm³) |
|-----------|-------------|---------|-------------|-----------------|----------------|
| ...       | ...         | ...     | ...         | ...             | ...            |

Sort by E/atom (ascending = most stable first).

## Step 4 — Report stability analysis
- **Most stable structure**: lowest E/atom; state energy difference from others (meV/atom)
- **Energy differences**: report in meV/atom relative to the most stable phase
- **Phase stability rule of thumb**: ΔE < 25 meV/atom — structures are close in stability (entropy/temperature effects may matter); ΔE > 100 meV/atom — clearly metastable
- **Structural comparison**: comment on density, coordination number, bond lengths
- **Caveats**:
  - For molecular crystals or layered materials (e.g., graphite), note that GGA misses van der Waals interactions — results may favour the wrong polymorph
  - If comparing across different compositions, energy per atom is not directly comparable — use formation energy from elemental references instead
- **Suggested next step**: if the user wants to check phase stability in detail, suggest running the Materials Project query via `qe_search_materials_project`
