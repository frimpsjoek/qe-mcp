---
description: Guide for structure creation and manipulation with ASE
name: ASE (Atomic Simulation Environment) Documentation
---
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