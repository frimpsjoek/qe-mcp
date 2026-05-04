---
description: Documentation for post-processing and visualization with pp.x
name: Quantum ESPRESSO pp.x Documentation
---
# Quantum ESPRESSO pp.x Documentation

## Overview
pp.x is a post-processing tool for extracting and visualizing data from
pw.x calculations. It can generate charge densities, potentials, orbitals,
and other quantities in various formats.

## Input File Structure

### &INPUTPP Namelist

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| prefix | STRING | 'pwscf' | Same prefix used in pw.x calculation |
| outdir | STRING | './' | Same outdir used in pw.x calculation |
| filplot | STRING | - | Output file for intermediate data |
| plot_num | INTEGER | - | Type of data to extract (see below) |
| spin_component | INTEGER | 0 | 0=total, 1=up, 2=down for spin-polarized |
| kpoint | INTEGER | 1 | k-point index for wavefunctions |
| kband | INTEGER | 1 | Band index for wavefunctions |
| lsign | LOGICAL | .false. | If true, plot sign of wavefunction |

### plot_num Values

| Value | Description |
|-------|-------------|
| 0 | Electron charge density |
| 1 | Total potential (V_bare + V_H + V_xc) |
| 2 | Local ionic potential V_bare |
| 3 | Local potential V_bare + V_H |
| 4 | Local potential V_bare + V_H + V_xc |
| 5 | |ψ|² for a selected state (needs kpoint, kband) |
| 6 | Spin polarization (ρ↑ - ρ↓) |
| 7 | Contribution of selected wavefunction to charge |
| 8 | Electron localization function (ELF) |
| 9 | Charge density minus superposition of atomic charges |
| 10 | ILDOS (integrated local DOS) |
| 11 | Bare + Hartree potential |
| 17 | All-electron charge from PAW |
| 21 | All-electron kinetic energy density from PAW |

### &PLOT Namelist

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| nfile | INTEGER | 1 | Number of data files |
| filepp(1) | STRING | - | First file from INPUTPP |
| weight(1) | REAL | 1.0 | Weight for combining files |
| iflag | INTEGER | - | Dimensionality: 0=1D, 1=1D, 2=2D, 3=3D, 4=2D polar |
| output_format | INTEGER | - | Output format (see below) |
| fileout | STRING | - | Output filename |
| e1, e2, e3 | 3 REALS | - | Vectors spanning the plotting region |
| x0 | 3 REALS | - | Origin of the plot |
| nx, ny, nz | INTEGER | - | Number of points along e1, e2, e3 |

### output_format Values

| Value | Description |
|-------|-------------|
| 0 | Format suitable for gnuplot (1D) |
| 1 | Format for contour.x (obsolete) |
| 2 | Format for plotrho.x (2D) |
| 3 | Format for XCRYSDEN (3D) |
| 4 | Format for gOpenMol (3D) |
| 5 | Format for XCRYSDEN (2D) |
| 6 | Gaussian cube format (3D) |
| 7 | gnuplot format (2D) |

## Example: Charge Density Cube File

```
&INPUTPP
    prefix = 'silicon'
    outdir = './tmp'
    filplot = 'charge.dat'
    plot_num = 0
/
&PLOT
    nfile = 1
    filepp(1) = 'charge.dat'
    iflag = 3
    output_format = 6
    fileout = 'charge.cube'
/
```

## Example: Wavefunction (Orbital) Plot

```
&INPUTPP
    prefix = 'molecule'
    outdir = './tmp'
    filplot = 'homo.dat'
    plot_num = 7
    kpoint = 1
    kband = 4
/
&PLOT
    nfile = 1
    filepp(1) = 'homo.dat'
    iflag = 3
    output_format = 6
    fileout = 'homo.cube'
/
```