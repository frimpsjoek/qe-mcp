---
description: Pre-calculation triage guide — ask, default, or confirm before running.
name: Pre-Calculation Guide
---
# Pre-Calculation Triage Guide

Before launching any QE calculation, follow this triage protocol to ensure
the user gets the right calculation with the right parameters. The goal is
to **never surprise the user** with an expensive job they did not intend,
while also **never blocking them** with unnecessary questions when sensible
defaults exist.

---

## 1. STRUCTURE RESOLUTION

When the user mentions a material, resolve the structure using this priority:

### Tier 1 — Built-in database (use immediately, no questions)
Over 80 materials are built in. If the user says a formula or common name
that matches the built-in database, use it directly:

| User says | Resolved as |
|-----------|-------------|
| "Si", "silicon" | Diamond cubic, a = 5.43 Å |
| "Cu", "copper" | FCC, a = 3.615 Å |
| "GaAs" | Zincblende, a = 5.65 Å |
| "graphene" | Honeycomb, a = 2.46 Å, 15 Å vacuum |
| "SrTiO3" | Cubic perovskite, a = 3.905 Å |
| "H2O", "water" | Molecule with 10 Å vacuum box |

**Action**: proceed directly. Mention to the user which structure you are using
(e.g., "Using diamond-cubic silicon with a = 5.43 Å").

### Tier 2 — Natural language (parse, then confirm if ambiguous)
The parser handles: `"Si bulk diamond cubic a = 5.43 angstrom"`,
`"Fe bcc a=2.87 A"`, coordinate blocks with cell info, etc.

**Action**: if parsing succeeds, briefly state the structure and proceed.
If parsing fails or the result seems unusual (e.g., very short bonds, zero
volume), ask the user to clarify.

### Tier 3 — Materials Project (if MP_API_KEY is set)
For materials not in the built-in database, search Materials Project:
1. `qe_search_materials_project(formula)` → find candidates
2. Present the top results (material ID, space group, energy above hull)
3. Let the user pick, or auto-select the ground-state entry (lowest
   energy above hull)
4. `qe_get_mp_structure(mp_id)` → load the selected structure

**Action**: always tell the user which MP entry you selected and why.

### Tier 4 — Ask the user
If none of the above work, ask for:
- A CIF/POSCAR/XYZ file path
- A Materials Project ID
- Explicit coordinates and cell parameters

**Do not guess exotic structures.** If the user says "calculate TiO2" and
you are unsure whether they mean anatase or rutile, ask.

### Polymorphs and ambiguous cases — always ask
Some materials have multiple common phases. When you encounter these, ask
the user which phase they want before proceeding:

| Material | Common phases | Default if user does not specify |
|----------|--------------|----------------------------------|
| TiO2 | Rutile, Anatase, Brookite | Ask |
| SiO2 | α-Quartz, Cristobalite, Amorphous | Ask |
| C | Diamond, Graphite, Graphene | Ask (unless "graphene" or "diamond" keyword used) |
| Fe | BCC (α), FCC (γ), HCP (ε) | BCC α-Fe (ground state) |
| BN | Hexagonal (h-BN), Cubic (c-BN) | Ask (unless "hBN" or "cubic BN" keyword used) |
| ZnS | Zincblende, Wurtzite | Zincblende (more common for ZnS) |
| SiC | 3C, 4H, 6H polytypes | 3C zincblende (built-in default) |
| Al2O3 | Corundum (α), γ-alumina | Ask (not in built-in database) |
| MnO2 | Pyrolusite (β), Ramsdellite, Birnessite | Ask |

---

## 2. CALCULATION TYPE RESOLUTION

If the user does not specify what kind of calculation they want, infer from
their question using these rules:

| User intent | Inferred calculation | Confidence |
|-------------|---------------------|------------|
| "Calculate [material]" (no specifics) | SCF (cheapest useful result) | Medium — confirm |
| "Is X a metal/semiconductor?" | Band structure | High |
| "Band gap of X" | Band structure | High |
| "Electronic structure" | Band structure | High |
| "Density of states" / "DOS" | DOS workflow | High |
| "Optimize" / "relax" | Geometry relaxation | High |
| "Lattice constant" | vc-relax | High |
| "Magnetic moment" / "magnetism" | SCF with spin_polarized=True | High |
| "Total energy" | SCF | High |
| "Compare X and Y" | SCF on both, compare E/atom | High |
| "Properties of X" | Ask — too broad | Low |

**For medium/low confidence**: briefly state what you plan to do and ask
if the user wants something different before launching.

Example:
> "I'll run a quick SCF calculation on silicon (diamond cubic, a = 5.43 Å)
> to get the total energy and Fermi level. Would you like something more
> detailed like a band structure or DOS instead?"

---

## 3. PARAMETER DEFAULTS — USE THESE, DON'T ASK

The server auto-selects good defaults. **Do not ask the user** about these
parameters unless they mention accuracy concerns:

| Parameter | Auto-selection logic |
|-----------|---------------------|
| `ecutwfc` | From pseudopotential hints (typically 40–80 Ry) |
| `ecutrho` | 4× ecutwfc (norm-conserving SG15 pseudopotentials) |
| `kpoints` | Auto-scaled to cell size: ~0.04 Å⁻¹ spacing |
| `smearing` | mv (cold) for metals, gaussian for insulators |
| `degauss` | 0.02 Ry for metals, 0.01 Ry for insulators |
| `spin_polarized` | Auto-enabled for Fe, Co, Ni, Mn, Cr, V, Gd, Eu |
| `mixing_beta` | 0.7 (default), reduced automatically for tricky systems |

**When to mention these to the user**: only if the calculation fails, or
if the user explicitly asks for "high accuracy" or "production quality".

---

## 4. CONFIRM-BEFORE-COMPUTE PROTOCOL

Before launching a calculation, give the user a brief summary. The level
of detail depends on the calculation cost:

### Quick calculations (SCF on small cells ≤ 10 atoms) — minimal confirmation
> "Running SCF on bulk silicon (2 atoms, diamond cubic). This should take
> under a minute."

### Medium calculations (band structure, DOS, relaxation) — state the plan
> "I'll run a full band structure workflow for GaAs:
> 1. SCF with auto k-grid
> 2. Non-SCF along Γ→X→W→L→Γ→K (100 k-points)
> 3. bands.x post-processing
>
> Using zincblende structure (a = 5.65 Å). Proceeding now."

### Expensive calculations (large cells, vc-relax, convergence sweeps) — ask first
> "A variable-cell relaxation on this 40-atom supercell will take a while
> on Polaris. The plan:
> - vc-relax with ecutwfc = 60 Ry, 4×4×4 k-grid
> - Estimated ~20 ionic steps
>
> Want me to go ahead, or adjust anything first?"

### Multi-step comparisons — always confirm the full plan
> "To compare BCC and FCC iron, I'll run:
> 1. SCF on Fe BCC (a = 2.87 Å, spin-polarized)
> 2. SCF on Fe FCC (a = 3.59 Å, spin-polarized)
> 3. Compare total energy per atom
>
> Shall I proceed?"

---

## 5. WHAT TO DO AFTER RESOLVING STRUCTURE

Once the structure is resolved, call `qe_validate_structure` to check:
- All elements have pseudopotentials
- No overlapping atoms (distances < 0.5 Å)
- Reasonable cell volume
- Appropriate k-points

If validation returns warnings, fix them or inform the user before proceeding.

---

## 6. KNOWLEDGE THE AGENT SHOULD SURFACE

When presenting results, always mention these caveats when relevant:

| Situation | What to tell the user |
|-----------|-----------------------|
| Band gap calculated | "DFT (GGA/PBE) underestimates band gaps by ~30–50%. Experimental gap for Si is 1.1 eV; DFT gives ~0.6 eV." |
| Magnetic calculation | "Magnetic moments are for the unit cell. Per-atom values are approximate for multi-atom cells." |
| Metal/insulator classification | "Classification is based on the DFT band structure. Strongly correlated materials may require DFT+U or hybrid functionals." |
| Relaxed lattice constant | "PBE tends to overestimate lattice constants by ~1%. PBEsol is often more accurate for solids." |
| Energy comparison | "Energy differences are more reliable than absolute energies. Report ΔE in meV/atom." |
| Missing vdW | "For layered/molecular systems, PBE lacks van der Waals corrections. Results for interlayer distances may be unreliable." |
| Spin-orbit coupling | "Spin-orbit coupling is not included. This matters for heavy elements (Bi, Pb, Au) and topological properties." |

---

## 7. WHEN TO USE MATERIALS PROJECT

Use MP proactively when:
- The material is **not in the built-in database** and the user gives only a formula
- The user asks about a **specific polymorph** that is not built in
- The user asks to **compare phases** — MP can provide all known polymorphs
- The user asks about **thermodynamic stability** — MP has formation energies and hull data

Do **not** use MP when:
- The material is in the built-in database (faster, no API dependency)
- The user provided their own structure file
- MP_API_KEY is not set — tell the user how to add it instead of silently failing

---

## 8. QUICK REFERENCE — COMMON USER REQUESTS

| User request | Agent action |
|--------------|-------------|
| "Calculate silicon" | SCF on built-in Si. Mention structure. Suggest bands/DOS after. |
| "Band structure of GaAs" | Band structure workflow. No questions needed. |
| "What is the band gap of MgO?" | Band structure workflow. Report gap + DFT caveat. |
| "Optimize gold" | vc-relax on built-in Au FCC. Report lattice constant. |
| "Compare diamond and graphite" | Confirm plan. SCF on both. Compare E/atom. Note vdW caveat for graphite. |
| "Is iron magnetic?" | SCF on Fe with spin_polarized=True. Report moment. |
| "Calculate TiO2" | Ask: rutile or anatase? Or search MP for both. |
| "Run a quick test on copper" | SCF on Cu. Use "low" accuracy (fewer k-points). |
| "I have a CIF file at /path/to/file.cif" | Load file, validate, ask what calculation to run. |
| "mp-149" | Load from Materials Project. Show structure. Ask what to calculate. |
