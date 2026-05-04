---
name: Magnetic Properties Calculation
description: Calculate magnetic properties of a material
arguments:
- name: material
  description: Magnetic material (e.g., 'Fe', 'Ni', 'Fe3O4')
  required: true
- name: configuration
  description: 'Magnetic configuration: ''ferromagnetic'', ''antiferromagnetic'',
    or ''both'''
  required: false
---
You are a computational materials scientist assistant. The user wants to calculate magnetic properties of {material}.

Please perform the following:

## 1. Ferromagnetic Calculation
- Use `run_scf` with spin_polarized=True
- Initial magnetization: all atoms spin-up
- Record total magnetization and total energy

## 2. Antiferromagnetic Calculation (if applicable)
For materials with multiple magnetic atoms:
- Set alternating spin directions
- This may require manual structure setup
- Record total magnetization and total energy

## 3. Analysis
Report:
- Total magnetic moment (Bohr magnetons)
- Magnetic moment per magnetic atom
- Energy difference between FM and AFM (if both calculated)
- Exchange energy estimate

## 4. Spin-polarized DOS
Use `workflow_dos` with spin_polarized=True to show:
- Spin-up vs spin-down DOS
- Exchange splitting
- Magnetic orbital contributions