---
description: Step-by-step guides for common DFT workflows
name: QE-MCP Workflow Guides
---
# QE-MCP Workflow Guides

## 1. Band Structure Calculation

### Purpose
Calculate electronic band structure to determine band gap, band character,
and electronic dispersion.

### Steps
1. **SCF** - Self-consistent ground state calculation
2. **NSCF (bands)** - Non-self-consistent calculation along k-path
3. **bands.x** - Extract and process band data

### QE-MCP Usage
```
workflow_bandstructure("Si")
workflow_bandstructure("GaAs", ecutwfc=60, npoints_band=100)
```

### Interpretation
- **Band gap**: Energy difference between VBM and CBM
- **Direct gap**: VBM and CBM at same k-point
- **Indirect gap**: VBM and CBM at different k-points
- **Metallic**: No gap, bands cross Fermi level

## 2. Density of States (DOS)

### Purpose
Calculate the density of electronic states as a function of energy.

### Steps
1. **SCF** - Self-consistent ground state
2. **NSCF** - Non-self-consistent on dense k-grid
3. **dos.x** - Calculate DOS

### QE-MCP Usage
```
workflow_dos("Cu")
workflow_dos("Fe", spin_polarized=True)
```

### Interpretation
- **Peaks**: High density of states at specific energies
- **Gap**: Zero DOS indicates band gap
- **Fermi level**: Position of chemical potential

## 3. Projected DOS (PDOS)

### Purpose
Decompose DOS into contributions from each atom and orbital type.

### Steps
1. **SCF** - Self-consistent ground state
2. **NSCF** - Non-self-consistent on dense k-grid
3. **projwfc.x** - Calculate projected DOS

### Interpretation
- **Orbital character**: Which orbitals contribute to each band
- **Hybridization**: Mixed orbital contributions indicate bonding
- **d-band center**: Important for catalysis

## 4. Geometry Optimization

### Purpose
Find the minimum energy structure (atomic positions and/or cell).

### Types
- **relax**: Optimize atomic positions only
- **vc-relax**: Optimize both positions and cell

### QE-MCP Usage
```
run_relax("molecule.xyz")
run_vc_relax("crystal.cif")
workflow_relax_and_scf("NaCl")
```

### Convergence Criteria
- **forc_conv_thr**: Force threshold (Ry/Bohr)
- **press_conv_thr**: Pressure threshold (kbar)
- **etot_conv_thr**: Energy threshold (Ry)

## 5. Adsorption Energy

### Purpose
Calculate the binding energy of a molecule on a surface.

### Formula
E_ads = E_slab+mol - E_slab - E_mol

### Steps
1. Optimize clean slab
2. Optimize isolated molecule
3. Add molecule to slab
4. Optimize combined system
5. Calculate energy difference

### Tips
- Use same k-grid and cutoffs for all calculations
- Ensure sufficient vacuum above surface
- Consider multiple adsorption sites
- Check for adsorbate-induced reconstructions

## 6. Convergence Testing

### Purpose
Ensure results are converged with respect to numerical parameters.

### Key Parameters
1. **ecutwfc**: Wavefunction cutoff
2. **ecutrho**: Charge density cutoff (typically 8-12x ecutwfc)
3. **k-points**: Brillouin zone sampling
4. **smearing**: For metals, degauss value

### Procedure
1. Fix all parameters except one
2. Vary the parameter and monitor total energy
3. Choose value where energy changes < 1 meV/atom

## 7. Spin-Polarized Calculations

### Purpose
Calculate magnetic systems with spin-dependent properties.

### Setup
```python
run_scf("Fe", spin_polarized=True)
```

### Key Parameters
- **nspin = 2**: Enable collinear spin polarization
- **starting_magnetization**: Initial spin for each species

### Outputs
- Total magnetization (Bohr magnetons)
- Spin-up and spin-down DOS
- Magnetic moments per atom

## 8. Common Issues and Solutions

### SCF Not Converging
- Increase mixing_ndim (try 12-16)
- Reduce mixing_beta (try 0.3-0.5)
- Use 'local-TF' mixing_mode for metals
- Add small smearing for metals

### Forces Not Converging
- Increase ecutwfc
- Improve k-point sampling
- Reduce forc_conv_thr gradually

### Memory Issues
- Reduce ecutwfc if possible
- Use fewer k-points
- Enable disk_io='low'

### Negative Frequencies in Phonons
- Structure not fully relaxed
- Reduce forc_conv_thr
- Check for symmetry issues