---
name: Convergence Testing Skill
description: Systematic ecutwfc and k-point convergence tests with automated tables and recommended parameters.
arguments:
  - name: material
    description: Material to test (e.g., 'Si', 'Cu', 'MgO')
    required: true
  - name: parameter
    description: "What to test: 'ecutwfc', 'kpoints', or 'both'"
    required: false
---
You are running systematic convergence tests for **{material}** (testing: {parameter}).

## Part A — Ecutwfc convergence (skip if parameter = "kpoints")

Run 6 SCF calculations with increasing plane-wave cutoffs, keeping kpoints fixed at [8, 8, 8]:

| Run | ecutwfc (Ry) | kpoints |
|-----|-------------|---------|
| 1   | 30          | [8,8,8] |
| 2   | 40          | [8,8,8] |
| 3   | 50          | [8,8,8] |
| 4   | 60          | [8,8,8] |
| 5   | 70          | [8,8,8] |
| 6   | 80          | [8,8,8] |

Call `qe_run_scf(structure="{material}", ecutwfc=<value>, kpoints=[8,8,8])` for each. Poll each job before starting the next. Record E_total (eV) for each run.

Build the convergence table:

| ecutwfc (Ry) | E_total (eV) | ΔE vs previous (meV/atom) | ΔE vs 80 Ry (meV/atom) |
|-------------|-------------|--------------------------|------------------------|
| 30           | ...         | —                        | ...                    |
| ...          | ...         | ...                      | ...                    |

**Recommendation**: choose the lowest ecutwfc where ΔE < 1 meV/atom from the next value.

## Part B — K-points convergence (skip if parameter = "ecutwfc")

Use the converged ecutwfc from Part A (or 60 Ry if Part A was skipped). Run 5 SCF calculations:

| Run | kpoints     |
|-----|-------------|
| 1   | [4, 4, 4]   |
| 2   | [6, 6, 6]   |
| 3   | [8, 8, 8]   |
| 4   | [10, 10, 10]|
| 5   | [12, 12, 12]|

Build the convergence table:

| k-grid       | E_total (eV) | ΔE vs previous (meV/atom) | ΔE vs 12³ (meV/atom) |
|-------------|-------------|--------------------------|----------------------|
| [4,4,4]      | ...         | —                        | ...                  |
| ...          | ...         | ...                      | ...                  |

**Recommendation**: choose the coarsest k-grid where ΔE < 1 meV/atom from the next denser grid.

## Final recommendation
Summarise the recommended parameters:
- `ecutwfc`: X Ry (converged to Y meV/atom)
- `kpoints`: [N, N, N] (converged to Y meV/atom)
- Estimated total calculation time with these parameters

Consult `qe://llm/decision-guide` for typical converged values for this material class as a sanity check.
