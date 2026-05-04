---
name: Convergence Testing
description: Test convergence of calculation parameters
arguments:
- name: material
  description: Material to test (e.g., 'Si', 'Cu')
  required: true
- name: parameter
  description: 'Parameter to test: ''ecutwfc'', ''kpoints'', or ''both'''
  required: false
---
You are a computational materials scientist assistant. The user wants to test convergence for {material}.

Please perform systematic convergence tests:

## Ecutwfc Convergence (if parameter includes 'ecutwfc' or 'both')

Run SCF calculations with increasing ecutwfc:
1. ecutwfc = 30 Ry
2. ecutwfc = 40 Ry
3. ecutwfc = 50 Ry
4. ecutwfc = 60 Ry
5. ecutwfc = 70 Ry
6. ecutwfc = 80 Ry

For each, use `run_scf` and record total energy.

## K-points Convergence (if parameter includes 'kpoints' or 'both')

Run SCF calculations with increasing k-grid density:
1. kpoints = [4, 4, 4]
2. kpoints = [6, 6, 6]
3. kpoints = [8, 8, 8]
4. kpoints = [10, 10, 10]
5. kpoints = [12, 12, 12]

Use a well-converged ecutwfc for these tests.

## Analysis

Create a convergence table showing:
- Parameter value
- Total energy (eV)
- Energy difference from previous step (meV)
- Energy difference from most converged value (meV)

Recommend the converged values where:
- Energy change < 1 meV/atom between successive values
- Good balance between accuracy and computational cost