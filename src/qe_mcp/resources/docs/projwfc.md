---
description: Documentation for projected DOS with projwfc.x
name: Quantum ESPRESSO projwfc.x Documentation
---
# Quantum ESPRESSO projwfc.x Documentation

## Overview
projwfc.x calculates the projected density of states (PDOS) onto atomic
orbitals, showing contributions from each atom and orbital type.

## Workflow
1. Run SCF calculation with pw.x (calculation='scf')
2. Run NSCF calculation with pw.x (calculation='nscf') on dense k-grid
3. Run projwfc.x to calculate PDOS

## Input File Structure

### &PROJWFC Namelist

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| prefix | STRING | 'pwscf' | Same prefix used in pw.x calculations |
| outdir | STRING | './' | Same outdir used in pw.x calculations |
| filpdos | STRING | prefix.pdos | Output PDOS file prefix |
| filproj | STRING | prefix.proj | Output projection file |
| ngauss | INTEGER | 0 | Type of gaussian broadening |
| degauss | REAL | 0.0 | Gaussian broadening (Ry) |
| Emin | REAL | - | Minimum energy (eV) |
| Emax | REAL | - | Maximum energy (eV) |
| DeltaE | REAL | 0.01 | Energy step (eV) |
| lsym | LOGICAL | .true. | Symmetrize projections |
| pawproj | LOGICAL | .false. | Use PAW all-electron wavefunctions |
| kresolveddos | LOGICAL | .false. | k-resolved DOS |
| tdosinboxes | LOGICAL | .false. | LDOS in boxes |
| plotboxes | LOGICAL | .false. | Plot boxes for LDOS |

## Example Input

```
&PROJWFC
    prefix = 'silicon'
    outdir = './tmp'
    filpdos = 'pdos'
    Emin = -10.0
    Emax = 15.0
    DeltaE = 0.01
    degauss = 0.02
/
```

## Output Files

### filpdos.pdos_atm#N(X)_wfc#M(l)
PDOS for atom N of species X, orbital M with angular momentum l.

Example filenames:
- `pdos.pdos_atm#1(Si)_wfc#1(s)` - Si atom 1, s orbital
- `pdos.pdos_atm#1(Si)_wfc#2(p)` - Si atom 1, p orbital
- `pdos.pdos_atm#2(O)_wfc#1(s)` - O atom 2, s orbital
- `pdos.pdos_atm#2(O)_wfc#2(p)` - O atom 2, p orbital

### Format
```
# E (eV)  ldos(E)  pdos(E)
 -10.000  0.0000   0.0000
  -9.990  0.0000   0.0000
...
```

### filpdos.pdos_tot
Total DOS summed over all projections.

## Plotting with Gnuplot

```gnuplot
set xlabel "Energy (eV)"
set ylabel "PDOS (states/eV)"
Ef = 6.233

plot 'pdos.pdos_atm#1(Si)_wfc#1(s)' u ($1-Ef):2 w l title "Si s", \
     'pdos.pdos_atm#1(Si)_wfc#2(p)' u ($1-Ef):2 w l title "Si p"
```