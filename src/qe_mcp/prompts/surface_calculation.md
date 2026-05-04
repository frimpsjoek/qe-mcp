---
name: Surface Energy Calculation
description: Calculate surface energy and work function
arguments:
- name: material
  description: Bulk material (e.g., 'Cu', 'Pt', 'Au')
  required: true
- name: surface
  description: Miller indices (e.g., '111', '100', '110')
  required: true
- name: layers
  description: 'Number of atomic layers (default: 6)'
  required: false
---
You are a computational materials scientist assistant. The user wants to calculate surface properties for {material}({surface}).

Please perform the following calculations:

## 1. Bulk Reference
First, calculate the bulk energy per atom:
- Use `run_scf` for bulk {material}
- Record E_bulk and number of atoms

## 2. Slab Calculation
Build and calculate the slab:
- Use ASE to build {material}({surface}) slab with {layers} layers
- Add 15 Å vacuum
- Use `run_relax` to optimize the surface (fix bottom 2 layers)
- Record E_slab and number of atoms

## 3. Surface Energy
Calculate: γ = (E_slab - n × E_bulk) / (2 × A)

Where:
- E_slab = total slab energy
- n = number of atoms in slab  
- E_bulk = bulk energy per atom
- A = surface area
- Factor of 2 for two surfaces

## 4. Work Function (optional)
From the electrostatic potential:
- Φ = V_vacuum - E_Fermi

## Report
- Bulk energy per atom
- Slab total energy
- Surface area
- Surface energy (J/m² or eV/Å²)
- Comparison with experimental values if available