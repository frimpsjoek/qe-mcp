---
description: Documentation for band structure extraction with bands.x
name: Quantum ESPRESSO bands.x Documentation
---
# Quantum ESPRESSO bands.x Documentation

## Overview
bands.x extracts band structure data from a non-self-consistent (NSCF)
calculation performed along a high-symmetry k-path.

## Workflow
1. Run SCF calculation with pw.x (calculation='scf')
2. Run NSCF calculation with pw.x (calculation='bands') along k-path
3. Run bands.x to extract and process band data

## Input File Structure

### &BANDS Namelist

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| prefix | STRING | 'pwscf' | Same prefix used in pw.x calculations |
| outdir | STRING | './' | Same outdir used in pw.x calculations |
| filband | STRING | 'bands.dat' | Output file with band data |
| spin_component | INTEGER | 1 | 1=up/total, 2=down for LSDA |
| lsigma(1) | LOGICAL | .false. | Compute expectation value of σ_x |
| lsigma(2) | LOGICAL | .false. | Compute expectation value of σ_y |
| lsigma(3) | LOGICAL | .false. | Compute expectation value of σ_z |
| lp | LOGICAL | .false. | Compute polarization for each k |
| filp | STRING | 'polarization.dat' | Output file for polarization |
| lsym | LOGICAL | .true. | Classify bands by symmetry |
| no_overlap | LOGICAL | .true. | Skip overlap matrix calculation |
| plot_2d | LOGICAL | .false. | 2D band structure plot |

## Example Input

```
&BANDS
    prefix = 'silicon'
    outdir = './tmp'
    filband = 'bands.dat'
/
```

## Output Files

### filband (bands.dat)
Contains band energies at each k-point:
```
 &plot nbnd=   8, nks=  100  /
          0.000000  0.000000  0.000000
   -5.7362   6.2329   6.2329   6.2329   8.7939   8.7939   8.7939   9.5619
          0.027196  0.027196  0.027196
   -5.7168   6.0115   6.2002   6.2002   8.8395   8.8426   8.8426   9.7039
...
```

### filband.gnu (bands.dat.gnu)
Gnuplot-friendly format:
```
# k-path coordinate    E_1    E_2    ...
   0.0000   -5.7362   6.2329   6.2329   6.2329   8.7939   ...
   0.0471   -5.7168   6.0115   6.2002   6.2002   8.8395   ...
```

## Plotting with Gnuplot

```gnuplot
set ylabel "Energy (eV)"
set xlabel "k-path"
set xtics ("Γ" 0, "X" 0.5, "M" 0.8536, "Γ" 1.207)
Ef = 6.233  # Fermi energy
plot for [i=2:9] 'bands.dat.gnu' u 1:(column(i)-Ef) w l notitle
```