---
description: Documentation for density of states calculations with dos.x
name: Quantum ESPRESSO dos.x Documentation
---
# Quantum ESPRESSO dos.x Documentation

## Overview
dos.x calculates the electronic density of states (DOS) from an NSCF
calculation performed on a dense k-point grid.

## Workflow
1. Run SCF calculation with pw.x (calculation='scf')
2. Run NSCF calculation with pw.x (calculation='nscf') on dense k-grid
3. Run dos.x to calculate DOS

## Input File Structure

### &DOS Namelist

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| prefix | STRING | 'pwscf' | Same prefix used in pw.x calculations |
| outdir | STRING | './' | Same outdir used in pw.x calculations |
| fildos | STRING | prefix.dos | Output DOS file |
| bz_sum | STRING | 'smearing' | 'smearing', 'tetrahedra', 'tetrahedra_lin', 'tetrahedra_opt' |
| ngauss | INTEGER | 0 | Type of gaussian broadening |
| degauss | REAL | 0.0 | Gaussian broadening (Ry) |
| Emin | REAL | - | Minimum energy (eV), default: lowest eigenvalue |
| Emax | REAL | - | Maximum energy (eV), default: highest eigenvalue |
| DeltaE | REAL | 0.01 | Energy step (eV) |

### ngauss Values

| Value | Method |
|-------|--------|
| 0 | Simple Gaussian |
| 1 | Methfessel-Paxton order 1 |
| -1 | Marzari-Vanderbilt "cold smearing" |
| -99 | Fermi-Dirac function |

## Example Input

```
&DOS
    prefix = 'silicon'
    outdir = './tmp'
    fildos = 'dos.dat'
    Emin = -10.0
    Emax = 15.0
    DeltaE = 0.01
    degauss = 0.02
/
```

## Output Format (dos.dat)

```
#  E (eV)   dos(E)     Int dos(E)
  -10.000   0.0000       0.0000
   -9.990   0.0000       0.0000
   ...
    0.000   2.3456      12.0000
   ...
```

Column 1: Energy (eV)
Column 2: DOS (states/eV/cell)
Column 3: Integrated DOS (states/cell)

## Plotting with Gnuplot

```gnuplot
set xlabel "Energy (eV)"
set ylabel "DOS (states/eV)"
Ef = 6.233  # Fermi energy
plot 'dos.dat' u ($1-Ef):2 w l title "Total DOS"
set arrow from 0,0 to 0,10 nohead lt 2
```