---
description: Information about SG15 pseudopotentials and cutoff recommendations
name: SG15 ONCV Pseudopotential Documentation
---
# SG15 ONCV Pseudopotential Documentation

## Overview
The SG15 pseudopotentials are optimized norm-conserving Vanderbilt (ONCV)
pseudopotentials designed for accurate and efficient DFT calculations.

## Key Features
- **Norm-conserving**: Exact charge within augmentation sphere
- **Optimized**: Multi-projector for high accuracy with low cutoff
- **Well-tested**: Verified against all-electron calculations
- **PBE functional**: Generated with PBE GGA exchange-correlation

## Available Elements
The SG15 library includes pseudopotentials for 69 elements (H-Bi, excluding
lanthanides and actinides):

H, He, Li, Be, B, C, N, O, F, Ne, Na, Mg, Al, Si, P, S, Cl, Ar, K, Ca,
Sc, Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn, Ga, Ge, As, Se, Br, Kr, Rb, Sr,
Y, Zr, Nb, Mo, Tc, Ru, Rh, Pd, Ag, Cd, In, Sn, Sb, Te, I, Xe, Cs, Ba,
La, Hf, Ta, W, Re, Os, Ir, Pt, Au, Hg, Tl, Pb, Bi

## Naming Convention
```
{Element}_ONCV_PBE-{version}.upf
{Element}_ONCV_PBE_FR-{version}.upf  (fully relativistic)
```

Examples:
- `Si_ONCV_PBE-1.2.upf` - Silicon, version 1.2
- `Fe_ONCV_PBE_FR-1.0.upf` - Iron, fully relativistic

## Recommended Cutoffs (ecutwfc in Ry)

| Element | ecutwfc | ecutrho (8x) |
|---------|---------|--------------|
| H | 40 | 320 |
| C, N, O | 50 | 400 |
| Si, P, S | 40 | 320 |
| Fe, Co, Ni | 55 | 440 |
| Cu, Zn | 50 | 400 |
| Ga, Ge, As | 45 | 360 |
| Ag, Au | 45 | 360 |
| Pt, Pd | 50 | 400 |

## QE-MCP Automatic Selection
QE-MCP automatically selects the best available pseudopotential:
1. First tries the latest version (e.g., -1.2)
2. Falls back to earlier versions if needed
3. Prefers scalar-relativistic over fully relativistic

## Validation and Testing
The SG15 pseudopotentials have been tested for:
- Lattice constants (< 1% error vs experiment)
- Bulk moduli (< 5% error)
- Cohesive energies (< 0.1 eV/atom error)
- Band gaps (DFT accuracy)
- Phonon frequencies

## References
- Hamann, D.R. "Optimized norm-conserving Vanderbilt pseudopotentials"
  Physical Review B 88, 085117 (2013)
- Schlipf, M. & Gygi, F. "Optimization algorithm for the generation of 
  ONCV pseudopotentials" Computer Physics Communications 196, 36 (2015)
- http://www.quantum-simulation.org/potentials/sg15_oncv/