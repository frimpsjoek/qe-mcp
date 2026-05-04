---
description: Example calculations with expected outputs.
name: Calculation Examples
---
# Example Calculations and Expected Outputs

## Example 1: "Is silicon a metal or semiconductor?"

**Tool**: `qe_workflow_bandstructure("Si")`

**Expected Output**:
```json
{
    "success": true,
    "band_gap_eV": 0.56,
    "is_metal": false,
    "vbm_eV": 6.23,
    "cbm_eV": 6.79
}
```

**Interpretation**: "Silicon is a semiconductor with an indirect band gap of 
approximately 0.56 eV (DFT typically underestimates the experimental value 
of 1.1 eV due to the band gap problem in DFT)."

---

## Example 2: "Calculate the magnetic moment of iron"

**Tool**: `qe_run_scf("Fe", spin_polarized=True)`

**Expected Output**:
```json
{
    "success": true,
    "total_energy_eV": -856.3,
    "total_magnetization": 2.2,
    "absolute_magnetization": 2.2
}
```

**Interpretation**: "Iron has a magnetic moment of about 2.2 μB per atom, 
consistent with its ferromagnetic ground state. This is close to the 
experimental value of 2.22 μB."

---

## Example 3: "What's the equilibrium lattice constant of copper?"

**Tools**: 
1. `qe_run_vc_relax("Cu")`
2. Check final cell parameters

**Expected Output**:
```json
{
    "success": true,
    "final_cell": [[3.63, 0, 0], [0, 3.63, 0], [0, 0, 3.63]],
    "pressure_kbar": 0.1
}
```

**Interpretation**: "The equilibrium lattice constant of copper is 
approximately 3.63 Å, which is close to the experimental value of 3.615 Å."

---

## Example 4: "Compare the stability of diamond and graphite"

**Tools**:
1. `qe_run_scf("C")` for diamond structure
2. `qe_run_scf(graphite_structure)` for graphite
3. Compare E/atom

**Interpretation**: Compare total energy per carbon atom. Lower energy 
means more stable. (Note: need vdW corrections for accurate graphite energy)

---

## Example 5: "Calculate DOS for TiO2 anatase"

**Tool**: `qe_workflow_dos("TiO2")`

**Expected Output**:
```json
{
    "success": true,
    "fermi_energy_eV": 5.2,
    "dos_file": "/path/to/dos.dat",
    "energy_range_eV": [-20, 15]
}
```

**Interpretation**: "TiO2 (anatase) shows a band gap in the DOS around 
the Fermi level. The valence band is primarily O 2p character, while 
the conduction band is Ti 3d character."