---
description: LLM decision guide for interpreting user requests.
name: LLM Decision Guide
---
# QE-MCP Decision Guide for Language Models

## How to Interpret User Requests

When a user asks about materials calculations, use this guide to determine
which tools to call and with what parameters.

---

## 1. DETECTING CALCULATION TYPES

### Band Structure Requests
Keywords: "band structure", "bands", "band gap", "electronic structure", 
          "semiconductor", "insulator", "metal", "direct gap", "indirect gap",
          "electronic bands", "dispersion"

→ Use: `qe_workflow_bandstructure(structure, ...)`

Examples:
- "Calculate the band structure of silicon" → workflow_bandstructure("Si")
- "Is GaAs a semiconductor?" → workflow_bandstructure("GaAs") then check band_gap_eV
- "What's the band gap of MgO?" → workflow_bandstructure("MgO")
- "Show me the electronic bands of copper" → workflow_bandstructure("Cu")

### DOS Requests
Keywords: "density of states", "DOS", "electronic density", "d-band",
          "orbital contributions", "PDOS", "projected DOS"

→ Use: `qe_workflow_dos(structure, ...)`

Examples:
- "Calculate DOS for iron" → workflow_dos("Fe", spin_polarized=True)
- "What does the density of states look like for TiO2?" → workflow_dos("TiO2")
- "Show the d-band of platinum" → workflow_dos("Pt")

### Geometry Optimization Requests
Keywords: "optimize", "relax", "minimize", "equilibrium", "stable structure",
          "relaxation", "geometry optimization", "find minimum"

→ Use: `qe_run_relax()` for fixed cell, `qe_run_vc_relax()` for full optimization

Examples:
- "Optimize the water molecule" → run_relax("H2O")
- "Find the equilibrium lattice constant of gold" → run_vc_relax("Au")
- "Relax the atomic positions in this crystal" → run_relax(structure)
- "Optimize both cell and positions" → run_vc_relax(structure)

### Single-Point Energy Requests
Keywords: "total energy", "ground state", "SCF", "self-consistent",
          "energy calculation", "electronic structure"

→ Use: `qe_run_scf(structure, ...)`

Examples:
- "Calculate the total energy of silicon" → run_scf("Si")
- "What's the ground state energy of Cu?" → run_scf("Cu")
- "Run an SCF calculation" → run_scf(structure)

### Magnetic Properties Requests
Keywords: "magnetic", "magnetism", "spin", "ferromagnetic", "antiferromagnetic",
          "magnetic moment", "spin-polarized", "magnetization"

→ Use any calculation with `spin_polarized=True`

Magnetic elements to auto-detect: Fe, Co, Ni, Mn, Cr, V, Gd, Eu
Magnetic compounds: Fe2O3, Fe3O4, NiO, CoO, MnO, CrO2

Examples:
- "Is iron magnetic?" → run_scf("Fe", spin_polarized=True)
- "Calculate the magnetic moment of nickel" → run_scf("Ni", spin_polarized=True)
- "Spin-polarized band structure of Fe" → workflow_bandstructure("Fe", spin_polarized=True)

---

## 2. AUTOMATIC PARAMETER SELECTION

### Ecutwfc (Wavefunction Cutoff)
The cutoff is automatically determined from pseudopotentials, but if user specifies:
- "quick/fast/test" → use lower cutoff (0.8× recommended)
- "accurate/precise/converged" → use higher cutoff (1.2× recommended)
- "production" → use recommended cutoff

### K-points
Automatic selection based on cell size. If user specifies:
- "quick/fast/test" → density="low"
- "accurate/precise/converged" → density="high"  
- "production/default" → density="medium"

For molecules and slabs:
- Non-periodic directions get Gamma (1 k-point)
- Check if structure has vacuum → likely surface/molecule

### Smearing
Auto-detect based on material type:
- **Metals** (Cu, Fe, Al, Au, Ag, Pt, Pd, Ni, etc.): 
  smearing="mv" (Marzari-Vanderbilt cold smearing), degauss=0.02
- **Semiconductors/Insulators** (Si, GaAs, MgO, TiO2, etc.):
  smearing="gaussian", degauss=0.01 (or fixed occupations)

### Spin Polarization
Auto-enable for:
- Pure magnetic elements: Fe, Co, Ni, Mn, Cr, V
- Magnetic compounds: anything containing Fe, Co, Ni, Mn, Cr in oxide form
- User mentions: "magnetic", "spin", "ferromagnetic", "antiferromagnetic"

---

## 3. WORKFLOW SELECTION

### Simple Questions → Single Tool
- "What elements have pseudopotentials?" → qe_list_pseudopotentials()
- "Load this structure file" → qe_load_structure(path)
- "Suggest k-points for Si" → qe_suggest_kpoints("Si")

### Property Questions → Full Workflow
- "Is X a metal/semiconductor?" → qe_workflow_bandstructure(X) then analyze
- "What's the band gap?" → qe_workflow_bandstructure(X) then check band_gap_eV
- "Electronic structure of X" → qe_workflow_bandstructure(X)

### Optimization Questions → Relaxation First
- "What's the equilibrium structure?" → qe_run_vc_relax() then qe_run_scf()
- "Optimize and calculate properties" → qe_workflow_relax_and_scf()

### Comparison Questions → Multiple Calculations
- "Compare Si and Ge" → Run same calculation on both, compare results
- "Which structure is more stable?" → Calculate energies, compare per-atom

---

## 4. RESULT INTERPRETATION

### Band Structure Results
```python
result = workflow_bandstructure("X")
if result["is_metal"]:
    # Explain: "X is metallic - bands cross the Fermi level"
elif result["band_gap_eV"] < 0.5:
    # Explain: "X is a small-gap semiconductor (gap = X.XX eV)"
elif result["band_gap_eV"] < 3.0:
    # Explain: "X is a semiconductor with band gap X.XX eV"
else:
    # Explain: "X is a wide-gap insulator (gap = X.XX eV)"
```

### Energy Comparisons
- Cohesive energy: E_bulk/atom - E_atom
- Formation energy: E_compound - sum(E_elements)
- Relative stability: Compare E/atom between phases

### Convergence
- Report if calculation converged (check "converged" field)
- If not converged, suggest: more steps, different mixing, check structure

---

## 5. MATERIAL CLASSIFICATION

### Automatic Material Type Detection

**Metals** (use smearing):
- Alkali: Li, Na, K, Rb, Cs
- Alkaline earth: Be, Mg, Ca, Sr, Ba
- Transition metals: Sc, Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn, Y, Zr, Nb, Mo, Tc, Ru, Rh, Pd, Ag, Cd, Hf, Ta, W, Re, Os, Ir, Pt, Au, Hg
- Post-transition: Al, Ga, In, Sn, Tl, Pb, Bi

**Semiconductors** (may need small smearing):
- Group IV: Si, Ge, SiC
- III-V: GaAs, GaN, InP, InAs, AlAs, GaP
- II-VI: ZnO, ZnS, ZnSe, CdS, CdSe, CdTe

**Insulators** (fixed occupations OK):
- Oxides: MgO, Al2O3, SiO2, TiO2
- Halides: NaCl, LiF, CaF2
- Nitrides: BN, Si3N4

**Magnetic** (spin-polarized):
- Fe, Co, Ni, Mn, Cr (pure metals)
- Fe2O3, Fe3O4, NiO, CoO, MnO (oxides)
- FeS2, NiS, CoS (sulfides)

---

## 6. ERROR HANDLING

### Common Issues and Suggestions

**"SCF not converging"**:
- Reduce mixing_beta to 0.3-0.4
- Increase mixing_ndim to 12
- For metals: ensure smearing is set
- Check for overlapping atoms

**"Negative frequencies"** (in phonon calculations):
- Structure not at minimum → run relax first
- Need tighter force convergence

**"Bands calculation failed"**:
- Check that SCF completed successfully
- Verify prefix and outdir match

**"Memory error"**:
- Reduce ecutwfc if possible
- Use fewer k-points
- Request more memory

---

## 7. BEST PRACTICES (from THEOS/EPFL)

### Exchange-Correlation Functional
- Default: PBE (what SG15 pseudopotentials use)
- For solids: PBEsol often better for lattice constants
- For vdW systems: need vdW-DF or DFT-D corrections

### Smearing (from Marzari's guidelines)
- **Always use Marzari-Vanderbilt (cold) smearing for metals**
- Typical degauss: 0.02 Ry (0.27 eV, ~3000 K effective)
- For accurate forces: converge smearing along with k-points
- Smearing helps SCF convergence even for semiconductors

### Convergence Testing
For production calculations, converge:
1. Ecutwfc: typically 1 meV/atom accuracy
2. K-points: typically 1 meV/atom accuracy  
3. Smearing (metals): check forces at different values

### Performance
- Use OMP_NUM_THREADS=1 (MPI parallelization is more efficient)
- For bands: can use fewer processes (I/O limited)