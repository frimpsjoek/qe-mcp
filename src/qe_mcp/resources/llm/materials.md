---
description: Common materials reference database.
name: Materials Database
---
# Common Materials Reference

## Elemental Metals

| Element | Structure | a (Å) | Type | Magnetic |
|---------|-----------|-------|------|----------|
| Li | BCC | 3.49 | Alkali | No |
| Na | BCC | 4.29 | Alkali | No |
| K | BCC | 5.23 | Alkali | No |
| Al | FCC | 4.05 | Metal | No |
| Cu | FCC | 3.615 | Noble | No |
| Ag | FCC | 4.09 | Noble | No |
| Au | FCC | 4.08 | Noble | No |
| Fe | BCC | 2.87 | Transition | Yes (FM) |
| Co | HCP | 2.51 | Transition | Yes (FM) |
| Ni | FCC | 3.52 | Transition | Yes (FM) |
| Cr | BCC | 2.91 | Transition | Yes (AFM) |
| Mn | Complex | 8.91 | Transition | Yes |
| Pt | FCC | 3.92 | Noble | No |
| Pd | FCC | 3.89 | Noble | No |
| Ti | HCP | 2.95 | Transition | No |
| Mo | BCC | 3.15 | Transition | No |
| W | BCC | 3.16 | Transition | No |

## Semiconductors

| Material | Structure | a (Å) | Gap (eV) | Type |
|----------|-----------|-------|----------|------|
| Si | Diamond | 5.43 | 1.1 | Indirect |
| Ge | Diamond | 5.66 | 0.67 | Indirect |
| C (dia) | Diamond | 3.57 | 5.5 | Indirect |
| GaAs | Zincblende | 5.65 | 1.42 | Direct |
| GaN | Wurtzite | 3.19 | 3.4 | Direct |
| InP | Zincblende | 5.87 | 1.34 | Direct |
| ZnO | Wurtzite | 3.25 | 3.4 | Direct |
| ZnS | Zincblende | 5.41 | 3.7 | Direct |

## Insulators

| Material | Structure | a (Å) | Gap (eV) |
|----------|-----------|-------|----------|
| MgO | Rocksalt | 4.21 | 7.8 |
| NaCl | Rocksalt | 5.64 | 8.5 |
| LiF | Rocksalt | 4.03 | 14.2 |
| Al2O3 | Corundum | - | 8.8 |
| SiO2 | Various | - | 9.0 |
| BN (cubic) | Zincblende | 3.62 | 6.4 |

## Typical DFT Parameters

| Material Type | ecutwfc (Ry) | K-grid (medium) | Smearing |
|---------------|--------------|-----------------|----------|
| Simple metal (Al) | 30-40 | 12x12x12 | mv, 0.02 |
| Transition metal | 50-60 | 16x16x16 | mv, 0.02 |
| Semiconductor | 40-50 | 8x8x8 | gaussian, 0.01 |
| Oxide | 60-80 | 6x6x6 | gaussian, 0.01 |
| Molecule | 50-60 | Gamma | fixed |