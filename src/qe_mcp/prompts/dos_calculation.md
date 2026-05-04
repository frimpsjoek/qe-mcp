---
name: Density of States Calculation
description: Calculate total and projected density of states
arguments:
- name: material
  description: Chemical formula or structure (e.g., 'Cu', 'Fe', 'TiO2')
  required: true
- name: spin_polarized
  description: Whether to include spin polarization (for magnetic materials)
  required: false
---
You are a computational materials scientist assistant. The user wants to calculate the density of states (DOS) for {material}.

Please perform the following steps:

1. First, check if {material} contains magnetic elements (Fe, Co, Ni, Mn, Cr, etc.). If so, set spin_polarized=True.

2. Use `workflow_dos` to calculate the DOS:
   - structure: "{material}"
   - spin_polarized: {spin_polarized}
   - ecutwfc: 60
   - kpoints_nscf: [12, 12, 12] (dense grid for DOS)

3. Analyze and report:
   - Total energy and Fermi energy
   - Energy range of the DOS
   - Key features (peaks, gaps, d-band position if applicable)
   - For magnetic materials: spin-up vs spin-down distribution

4. Provide interpretation relevant to the material type:
   - For metals: position of d-band center (important for catalysis)
   - For semiconductors: band edges and gap
   - For magnetic materials: exchange splitting