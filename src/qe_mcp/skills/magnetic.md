---
name: Magnetic Properties Skill
description: Calculate magnetic ground state (FM/AFM), magnetic moments, exchange energy, and spin-polarized DOS for magnetic materials.
arguments:
  - name: material
    description: Magnetic material (e.g., 'Fe', 'Ni', 'MnO', 'Fe3O4')
    required: true
  - name: configuration
    description: "Magnetic configuration to calculate: 'ferromagnetic', 'antiferromagnetic', or 'both'"
    required: false
---
You are calculating the magnetic properties of **{material}**.

## Step 1 — Ferromagnetic calculation
Run a spin-polarized SCF with all spins aligned:
```
qe_run_scf(
    structure="{material}",
    spin_polarized=True
)
```
Poll `qe_get_job_status` until complete. Record:
- `E_FM` (total energy, eV)
- `total_magnetization` (μB per unit cell)
- `absolute_magnetization` (μB per unit cell)
- Magnetic moment per magnetic atom

## Step 2 — Antiferromagnetic calculation (if configuration = "antiferromagnetic" or "both")
If the structure contains ≥2 inequivalent magnetic sites (e.g., two Fe sublattices in MnO or Fe2O3):
- Describe to the user how to set alternating starting_magnetization values to initialise the AFM state
- Run a second `qe_run_scf` with the alternating spin initialisation
- Poll until complete. Record `E_AFM`.

If only one magnetic sublattice exists, skip this step and explain why.

## Step 3 — Exchange energy and ground state
If both FM and AFM were calculated:
- Compute ΔE = E_AFM − E_FM (meV/magnetic atom)
- If ΔE > 0: FM is the ground state
- If ΔE < 0: AFM is the ground state
- Report the magnitude — typical values: Fe ~100 meV (strongly FM), MnO ~10 meV (weakly AFM)

## Step 4 — Spin-polarized DOS
Run the DOS workflow on the ground-state configuration:
```
qe_workflow_dos(
    structure="{material}",
    spin_polarized=True,
    kpoints_nscf=[12, 12, 12]
)
```
Poll until complete, then call `qe_read_dos` and `qe_read_pdos`.

## Step 5 — Report
- **Magnetic moment per atom** (μB) — compare with experimental values from `qe://llm/materials`
- **Ground state**: FM or AFM, and ΔE (meV/atom)
- **Exchange splitting** in the DOS (separation between majority and minority spin peaks)
- **Half-metallicity check**: if only one spin channel has states at E_Fermi, flag as potential half-metal
- **DFT caveat**: GGA often overestimates moments in itinerant magnets (e.g., Fe ~2.2 μB vs exp 2.22 μB is accurate, but some oxides need DFT+U for correct description — suggest `skill_dft_u` if applicable)
