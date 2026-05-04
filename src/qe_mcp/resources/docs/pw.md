---
description: Complete documentation for pw.x SCF and relaxation calculations
name: Quantum ESPRESSO pw.x Documentation
---
# Quantum ESPRESSO pw.x Documentation

## Overview
pw.x is the main program for self-consistent field (SCF) calculations,
structural optimization, and molecular dynamics in Quantum ESPRESSO.

## Input File Structure

The input file consists of NAMELISTS and CARDS:

### NAMELISTS

#### &CONTROL
Controls the type of calculation and I/O.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| calculation | STRING | 'scf' | Type: 'scf', 'relax', 'vc-relax', 'md', 'vc-md', 'bands', 'nscf' |
| prefix | STRING | 'pwscf' | Prepended to I/O filenames |
| outdir | STRING | './' | Directory for large files (tmp, wfc, etc.) |
| pseudo_dir | STRING | './' | Directory containing pseudopotential files |
| verbosity | STRING | 'low' | 'low' or 'high' output verbosity |
| tprnfor | LOGICAL | .false. | Print forces |
| tstress | LOGICAL | .false. | Print stress tensor |
| etot_conv_thr | REAL | 1.0D-4 | Energy convergence threshold (Ry) |
| forc_conv_thr | REAL | 1.0D-3 | Force convergence threshold (Ry/Bohr) |
| nstep | INTEGER | 50 | Max ionic steps for relaxation/MD |
| disk_io | STRING | 'low' | Disk I/O: 'high', 'medium', 'low', 'none' |

#### &SYSTEM
Describes the system under study.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| ibrav | INTEGER | - | Bravais lattice index (0=free, 1=cubic P, 2=cubic F, 3=cubic I, etc.) |
| celldm(1) | REAL | - | Lattice parameter a (Bohr) when ibrav≠0 |
| A, B, C | REAL | - | Lattice parameters (Angstrom) when ibrav=0 |
| nat | INTEGER | - | Number of atoms in unit cell |
| ntyp | INTEGER | - | Number of atomic species |
| ecutwfc | REAL | - | Kinetic energy cutoff for wavefunctions (Ry) |
| ecutrho | REAL | 4*ecutwfc | Kinetic energy cutoff for charge density (Ry) |
| occupations | STRING | 'fixed' | 'fixed', 'smearing', 'tetrahedra', 'tetrahedra_lin', 'tetrahedra_opt' |
| smearing | STRING | 'gaussian' | 'gaussian', 'methfessel-paxton', 'marzari-vanderbilt', 'fermi-dirac', 'cold' |
| degauss | REAL | 0.0 | Smearing width (Ry) |
| nspin | INTEGER | 1 | 1=non-spin-polarized, 2=spin-polarized, 4=noncollinear |
| nbnd | INTEGER | - | Number of bands (default: enough for all electrons + some empty) |
| tot_charge | REAL | 0.0 | Total system charge |
| input_dft | STRING | - | Override XC functional from pseudopotential |
| vdw_corr | STRING | 'none' | Van der Waals correction: 'grimme-d2', 'grimme-d3', 'dft-d3', etc. |
| lda_plus_u | LOGICAL | .false. | Enable DFT+U |
| nosym | LOGICAL | .false. | Disable symmetry |
| noinv | LOGICAL | .false. | Disable time reversal symmetry |

#### &ELECTRONS
Controls the electronic self-consistency loop.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| electron_maxstep | INTEGER | 100 | Max SCF iterations |
| conv_thr | REAL | 1.0D-6 | SCF convergence threshold (Ry) |
| mixing_mode | STRING | 'plain' | 'plain', 'TF', 'local-TF' |
| mixing_beta | REAL | 0.7 | Mixing factor for self-consistency |
| mixing_ndim | INTEGER | 8 | Number of iterations for mixing |
| diagonalization | STRING | 'david' | 'david', 'cg', 'ppcg', 'paro', 'rmm-davidson' |
| diago_thr_init | REAL | - | Initial threshold for iterative diagonalization |
| diago_full_acc | LOGICAL | .false. | Full accuracy in diagonalization |

#### &IONS (for relaxation/MD)
Controls ionic motion.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| ion_dynamics | STRING | 'bfgs' | 'bfgs', 'damp', 'verlet', 'langevin', etc. |
| upscale | REAL | 100.0 | Max reduction factor for conv_thr during optimization |
| bfgs_ndim | INTEGER | 1 | Number of old forces/positions for BFGS |
| trust_radius_max | REAL | 0.8 | Max displacement in BFGS (Bohr) |
| trust_radius_min | REAL | 1.D-3 | Min displacement in BFGS (Bohr) |
| trust_radius_ini | REAL | 0.5 | Initial displacement in BFGS (Bohr) |

#### &CELL (for vc-relax/vc-md)
Controls cell dynamics.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| cell_dynamics | STRING | 'bfgs' | 'bfgs', 'damp-pr', 'damp-w', 'sd' |
| press | REAL | 0.0 | Target pressure (kbar) |
| press_conv_thr | REAL | 0.5 | Pressure convergence threshold (kbar) |
| cell_dofree | STRING | 'all' | Cell DOFs: 'all', 'x', 'y', 'z', 'xy', 'xz', 'yz', 'xyz', 'shape', 'volume', '2Dxy', '2Dshape' |

### CARDS

#### ATOMIC_SPECIES
```
ATOMIC_SPECIES
  Si  28.086  Si.pbe-n-kjpaw_psl.1.0.0.UPF
  O   15.999  O.pbe-n-kjpaw_psl.1.0.0.UPF
```
Format: symbol mass pseudopotential_file

#### ATOMIC_POSITIONS { crystal | angstrom | bohr | alat }
```
ATOMIC_POSITIONS crystal
  Si  0.00  0.00  0.00
  Si  0.25  0.25  0.25
```

#### K_POINTS { automatic | gamma | crystal | crystal_b | tpiba | tpiba_b }
```
K_POINTS automatic
  8 8 8  0 0 0
```
For automatic: nk1 nk2 nk3 sk1 sk2 sk3 (grid and shift)

#### CELL_PARAMETERS { angstrom | bohr | alat }
```
CELL_PARAMETERS angstrom
  5.43  0.00  0.00
  0.00  5.43  0.00
  0.00  0.00  5.43
```

## Typical Cutoff Values (ecutwfc in Ry)

| Element Type | NC-PP | US-PP | PAW |
|--------------|-------|-------|-----|
| s,p elements | 30-40 | 25-35 | 35-45 |
| d elements   | 40-50 | 35-45 | 45-55 |
| f elements   | 50-70 | 45-60 | 55-75 |

## Example Input Files

### SCF Calculation
```
&CONTROL
    calculation = 'scf'
    prefix = 'silicon'
    outdir = './tmp'
    pseudo_dir = './pseudo'
/
&SYSTEM
    ibrav = 2
    celldm(1) = 10.26
    nat = 2
    ntyp = 1
    ecutwfc = 40
    ecutrho = 320
/
&ELECTRONS
    conv_thr = 1.0d-8
    mixing_beta = 0.7
/
ATOMIC_SPECIES
  Si  28.086  Si_ONCV_PBE-1.2.upf
ATOMIC_POSITIONS crystal
  Si  0.00  0.00  0.00
  Si  0.25  0.25  0.25
K_POINTS automatic
  8 8 8  0 0 0
```

### Relaxation
```
&CONTROL
    calculation = 'relax'
    prefix = 'molecule'
    outdir = './tmp'
    pseudo_dir = './pseudo'
    forc_conv_thr = 1.0d-4
/
&SYSTEM
    ibrav = 0
    nat = 3
    ntyp = 2
    ecutwfc = 50
/
&ELECTRONS
    conv_thr = 1.0d-8
/
&IONS
    ion_dynamics = 'bfgs'
/
...
```

### Variable-Cell Relaxation
```
&CONTROL
    calculation = 'vc-relax'
    prefix = 'crystal'
    outdir = './tmp'
    pseudo_dir = './pseudo'
    forc_conv_thr = 1.0d-4
/
&SYSTEM
    ibrav = 0
    nat = 4
    ntyp = 2
    ecutwfc = 60
/
&ELECTRONS
    conv_thr = 1.0d-8
/
&IONS
    ion_dynamics = 'bfgs'
/
&CELL
    cell_dynamics = 'bfgs'
    press = 0.0
    press_conv_thr = 0.1
    cell_dofree = 'all'
/
...
```