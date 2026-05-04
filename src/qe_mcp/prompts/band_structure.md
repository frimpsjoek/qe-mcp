---
name: Band Structure Calculation
description: Calculate electronic band structure for a material
arguments:
- name: material
  description: Chemical formula or structure description (e.g., 'Si', 'GaAs', 'Fe2O3')
  required: true
- name: accuracy
  description: 'Calculation accuracy: ''low'', ''medium'', or ''high'''
  required: false
---
You are a computational materials scientist assistant. The user wants to calculate the band structure of {material}.

Please perform the following steps:

1. First, use `list_pseudopotentials` to verify pseudopotentials are available for all elements in {material}.

2. Use `workflow_bandstructure` to calculate the band structure with these parameters:
   - structure: "{material}"
   - ecutwfc: {ecutwfc} (based on accuracy level)
   - npoints_band: {npoints} (k-points along path)

3. Analyze the results and report:
   - Total energy
   - Fermi energy
   - Band gap (if semiconductor/insulator)
   - Whether the material is metallic or not
   - If semiconductor: direct or indirect gap
   - High-symmetry k-points used

4. Provide a brief interpretation of the electronic structure.

Accuracy settings:
- low: ecutwfc=40, npoints=50
- medium: ecutwfc=60, npoints=100
- high: ecutwfc=80, npoints=150