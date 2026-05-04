"""
Documentation resources for QE-MCP.

Contains comprehensive documentation for Quantum ESPRESSO and ASE,
formatted as MCP resources that LLMs can access.
"""

# =============================================================================
# QUANTUM ESPRESSO PW.X DOCUMENTATION
# =============================================================================

QE_PW_DOCS = """
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
"""

# =============================================================================
# QUANTUM ESPRESSO PP.X DOCUMENTATION
# =============================================================================

QE_PP_DOCS = """
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
"""

# =============================================================================
# QUANTUM ESPRESSO BANDS.X DOCUMENTATION
# =============================================================================

QE_BANDS_DOCS = """
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
"""

# =============================================================================
# QUANTUM ESPRESSO DOS.X DOCUMENTATION
# =============================================================================

QE_DOS_DOCS = """
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
"""

# =============================================================================
# QUANTUM ESPRESSO PROJWFC.X DOCUMENTATION
# =============================================================================

QE_PROJWFC_DOCS = """
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

plot 'pdos.pdos_atm#1(Si)_wfc#1(s)' u ($1-Ef):2 w l title "Si s", \\
     'pdos.pdos_atm#1(Si)_wfc#2(p)' u ($1-Ef):2 w l title "Si p"
```
"""

# =============================================================================
# ASE DOCUMENTATION
# =============================================================================

ASE_DOCS = """
# ASE (Atomic Simulation Environment) Documentation

## Overview
ASE is a Python library for setting up, running, and analyzing atomistic
simulations. QE-MCP uses ASE for structure I/O and manipulation.

## Creating Structures

### From Formula (Bulk)
```python
from ase.build import bulk

# FCC metals
cu = bulk('Cu', 'fcc', a=3.6)
al = bulk('Al', 'fcc', a=4.05)

# BCC metals
fe = bulk('Fe', 'bcc', a=2.87)
w = bulk('W', 'bcc', a=3.16)

# Diamond structure
si = bulk('Si', 'diamond', a=5.43)
ge = bulk('Ge', 'diamond', a=5.66)

# Zinc blende
gaas = bulk('GaAs', 'zincblende', a=5.65)
zns = bulk('ZnS', 'zincblende', a=5.41)

# Wurtzite
gan = bulk('GaN', 'wurtzite', a=3.19, c=5.19)
zno = bulk('ZnO', 'wurtzite', a=3.25, c=5.21)

# Rocksalt
nacl = bulk('NaCl', 'rocksalt', a=5.64)
mgo = bulk('MgO', 'rocksalt', a=4.21)

# HCP metals
ti = bulk('Ti', 'hcp', a=2.95, c=4.68)
zn = bulk('Zn', 'hcp', a=2.66, c=4.95)
```

### From Formula (Molecules)
```python
from ase.build import molecule

h2o = molecule('H2O')
co2 = molecule('CO2')
ch4 = molecule('CH4')
nh3 = molecule('NH3')
c6h6 = molecule('C6H6')  # Benzene
```

### Building Surfaces
```python
from ase.build import fcc111, fcc100, bcc110

# FCC(111) surface with 4 layers, 2x2 supercell
slab = fcc111('Au', size=(2, 2, 4), vacuum=10.0)

# FCC(100) surface
slab = fcc100('Pt', size=(3, 3, 4), vacuum=10.0)

# BCC(110) surface
slab = bcc110('Fe', size=(2, 2, 4), vacuum=10.0)
```

### Adding Adsorbates
```python
from ase.build import add_adsorbate

# Add CO to FCC(111) surface
slab = fcc111('Pt', size=(2, 2, 4), vacuum=10.0)
co = molecule('CO')
add_adsorbate(slab, co, height=2.0, position='ontop')
```

### From File
```python
from ase.io import read, write

# Read various formats
atoms = read('POSCAR')           # VASP
atoms = read('structure.cif')    # CIF
atoms = read('structure.xyz')    # XYZ
atoms = read('structure.pdb')    # PDB
atoms = read('input.in')         # QE input

# Write various formats
write('POSCAR', atoms)
write('output.cif', atoms)
write('output.xyz', atoms)
```

## Structure Manipulation

### Supercells
```python
from ase.build import make_supercell
import numpy as np

atoms = bulk('Si')
# 2x2x2 supercell
supercell = atoms * (2, 2, 2)

# General supercell
P = np.array([[2, 0, 0],
              [0, 2, 0],
              [0, 0, 1]])
supercell = make_supercell(atoms, P)
```

### Modifying Positions
```python
# Translate all atoms
atoms.translate([1.0, 0.0, 0.0])

# Rotate structure
atoms.rotate(45, 'z')  # 45 degrees around z-axis

# Center in cell
atoms.center()

# Set individual positions
atoms.positions[0] = [0.0, 0.0, 0.0]
```

### Modifying Cell
```python
# Set cell directly
atoms.set_cell([[a, 0, 0], [0, b, 0], [0, 0, c]])

# Scale cell (and positions)
atoms.set_cell(atoms.cell * 1.05, scale_atoms=True)

# Add vacuum
atoms.center(vacuum=10.0, axis=2)  # 10 Å vacuum along z
```

## Common Structure Properties

```python
# Number of atoms
n = len(atoms)

# Chemical formula
formula = atoms.get_chemical_formula()

# Get positions
positions = atoms.get_positions()  # Cartesian
scaled = atoms.get_scaled_positions()  # Fractional

# Get cell
cell = atoms.get_cell()
volume = atoms.get_volume()

# Get symbols
symbols = atoms.get_chemical_symbols()

# Check periodicity
pbc = atoms.get_pbc()  # [True, True, True] for 3D periodic
```

## High-Symmetry K-Paths

```python
from ase.dft.kpoints import bandpath

# Get k-path for band structure
path = atoms.cell.bandpath()
kpts = path.kpts  # K-point coordinates
special_points = path.special_points  # Dict of special points

# Specific path
path = atoms.cell.bandpath('GXWKGLUWLK', npoints=100)

# Common paths by crystal system:
# FCC: GXWKGLUWLK or GXWLGK
# BCC: GHNGPH or GNPHP
# HCP: GMKGALHA
# Cubic: GXMGRX or GXMG
```

## Supported File Formats

| Format | Read | Write | Extensions |
|--------|------|-------|------------|
| VASP | ✓ | ✓ | POSCAR, CONTCAR |
| CIF | ✓ | ✓ | .cif |
| XYZ | ✓ | ✓ | .xyz |
| PDB | ✓ | ✓ | .pdb |
| Quantum ESPRESSO | ✓ | ✓ | .in, .out |
| XCrySDen | ✓ | ✓ | .xsf |
| Cube | ✓ | ✓ | .cube |
| Trajectory | ✓ | ✓ | .traj |
| JSON | ✓ | ✓ | .json |
| GPAW | ✓ | ✓ | .gpw |
| FHI-aims | ✓ | ✓ | geometry.in |
| CASTEP | ✓ | ✓ | .cell |
| LAMMPS | ✓ | ✓ | .lmp |
"""

# =============================================================================
# SG15 PSEUDOPOTENTIAL DOCUMENTATION
# =============================================================================

PSEUDOPOTENTIAL_DOCS = """
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
"""

# =============================================================================
# WORKFLOW GUIDES
# =============================================================================

WORKFLOW_GUIDES = """
# QE-MCP Workflow Guides

## 1. Band Structure Calculation

### Purpose
Calculate electronic band structure to determine band gap, band character,
and electronic dispersion.

### Steps
1. **SCF** - Self-consistent ground state calculation
2. **NSCF (bands)** - Non-self-consistent calculation along k-path
3. **bands.x** - Extract and process band data

### QE-MCP Usage
```
workflow_bandstructure("Si")
workflow_bandstructure("GaAs", ecutwfc=60, npoints_band=100)
```

### Interpretation
- **Band gap**: Energy difference between VBM and CBM
- **Direct gap**: VBM and CBM at same k-point
- **Indirect gap**: VBM and CBM at different k-points
- **Metallic**: No gap, bands cross Fermi level

## 2. Density of States (DOS)

### Purpose
Calculate the density of electronic states as a function of energy.

### Steps
1. **SCF** - Self-consistent ground state
2. **NSCF** - Non-self-consistent on dense k-grid
3. **dos.x** - Calculate DOS

### QE-MCP Usage
```
workflow_dos("Cu")
workflow_dos("Fe", spin_polarized=True)
```

### Interpretation
- **Peaks**: High density of states at specific energies
- **Gap**: Zero DOS indicates band gap
- **Fermi level**: Position of chemical potential

## 3. Projected DOS (PDOS)

### Purpose
Decompose DOS into contributions from each atom and orbital type.

### Steps
1. **SCF** - Self-consistent ground state
2. **NSCF** - Non-self-consistent on dense k-grid
3. **projwfc.x** - Calculate projected DOS

### Interpretation
- **Orbital character**: Which orbitals contribute to each band
- **Hybridization**: Mixed orbital contributions indicate bonding
- **d-band center**: Important for catalysis

## 4. Geometry Optimization

### Purpose
Find the minimum energy structure (atomic positions and/or cell).

### Types
- **relax**: Optimize atomic positions only
- **vc-relax**: Optimize both positions and cell

### QE-MCP Usage
```
run_relax("molecule.xyz")
run_vc_relax("crystal.cif")
workflow_relax_and_scf("NaCl")
```

### Convergence Criteria
- **forc_conv_thr**: Force threshold (Ry/Bohr)
- **press_conv_thr**: Pressure threshold (kbar)
- **etot_conv_thr**: Energy threshold (Ry)

## 5. Adsorption Energy

### Purpose
Calculate the binding energy of a molecule on a surface.

### Formula
E_ads = E_slab+mol - E_slab - E_mol

### Steps
1. Optimize clean slab
2. Optimize isolated molecule
3. Add molecule to slab
4. Optimize combined system
5. Calculate energy difference

### Tips
- Use same k-grid and cutoffs for all calculations
- Ensure sufficient vacuum above surface
- Consider multiple adsorption sites
- Check for adsorbate-induced reconstructions

## 6. Convergence Testing

### Purpose
Ensure results are converged with respect to numerical parameters.

### Key Parameters
1. **ecutwfc**: Wavefunction cutoff
2. **ecutrho**: Charge density cutoff (typically 8-12x ecutwfc)
3. **k-points**: Brillouin zone sampling
4. **smearing**: For metals, degauss value

### Procedure
1. Fix all parameters except one
2. Vary the parameter and monitor total energy
3. Choose value where energy changes < 1 meV/atom

## 7. Spin-Polarized Calculations

### Purpose
Calculate magnetic systems with spin-dependent properties.

### Setup
```python
run_scf("Fe", spin_polarized=True)
```

### Key Parameters
- **nspin = 2**: Enable collinear spin polarization
- **starting_magnetization**: Initial spin for each species

### Outputs
- Total magnetization (Bohr magnetons)
- Spin-up and spin-down DOS
- Magnetic moments per atom

## 8. Common Issues and Solutions

### SCF Not Converging
- Increase mixing_ndim (try 12-16)
- Reduce mixing_beta (try 0.3-0.5)
- Use 'local-TF' mixing_mode for metals
- Add small smearing for metals

### Forces Not Converging
- Increase ecutwfc
- Improve k-point sampling
- Reduce forc_conv_thr gradually

### Memory Issues
- Reduce ecutwfc if possible
- Use fewer k-points
- Enable disk_io='low'

### Negative Frequencies in Phonons
- Structure not fully relaxed
- Reduce forc_conv_thr
- Check for symmetry issues
"""

# =============================================================================
# Resource Access Functions
# =============================================================================

RESOURCES = {
    "qe://docs/pw": {
        "name": "Quantum ESPRESSO pw.x Documentation",
        "description": "Complete documentation for pw.x SCF and relaxation calculations",
        "content": QE_PW_DOCS,
        "mimeType": "text/markdown",
    },
    "qe://docs/pp": {
        "name": "Quantum ESPRESSO pp.x Documentation",
        "description": "Documentation for post-processing and visualization with pp.x",
        "content": QE_PP_DOCS,
        "mimeType": "text/markdown",
    },
    "qe://docs/bands": {
        "name": "Quantum ESPRESSO bands.x Documentation",
        "description": "Documentation for band structure extraction with bands.x",
        "content": QE_BANDS_DOCS,
        "mimeType": "text/markdown",
    },
    "qe://docs/dos": {
        "name": "Quantum ESPRESSO dos.x Documentation",
        "description": "Documentation for density of states calculations with dos.x",
        "content": QE_DOS_DOCS,
        "mimeType": "text/markdown",
    },
    "qe://docs/projwfc": {
        "name": "Quantum ESPRESSO projwfc.x Documentation",
        "description": "Documentation for projected DOS with projwfc.x",
        "content": QE_PROJWFC_DOCS,
        "mimeType": "text/markdown",
    },
    "qe://docs/ase": {
        "name": "ASE (Atomic Simulation Environment) Documentation",
        "description": "Guide for structure creation and manipulation with ASE",
        "content": ASE_DOCS,
        "mimeType": "text/markdown",
    },
    "qe://docs/pseudopotentials": {
        "name": "SG15 ONCV Pseudopotential Documentation",
        "description": "Information about SG15 pseudopotentials and cutoff recommendations",
        "content": PSEUDOPOTENTIAL_DOCS,
        "mimeType": "text/markdown",
    },
    "qe://docs/workflows": {
        "name": "QE-MCP Workflow Guides",
        "description": "Step-by-step guides for common DFT workflows",
        "content": WORKFLOW_GUIDES,
        "mimeType": "text/markdown",
    },
}


def list_resources() -> list[dict]:
    """List all available documentation resources."""
    return [
        {
            "uri": uri,
            "name": info["name"],
            "description": info["description"],
            "mimeType": info["mimeType"],
        }
        for uri, info in RESOURCES.items()
    ]


def get_resource(uri: str) -> dict | None:
    """Get a specific resource by URI."""
    if uri in RESOURCES:
        return {
            "uri": uri,
            "name": RESOURCES[uri]["name"],
            "mimeType": RESOURCES[uri]["mimeType"],
            "text": RESOURCES[uri]["content"],
        }
    return None
