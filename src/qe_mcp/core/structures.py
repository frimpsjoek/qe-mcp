"""
Structure I/O utilities.

Load and manipulate atomic structures using ASE.
Supports: CIF, POSCAR/VASP, XYZ, extxyz, Materials Project, and built-in structures.
"""

from pathlib import Path
from io import StringIO
from typing import Any, Optional
import os
import re

from ase import Atoms
from ase.io import read, write
from ase.build import bulk, molecule, surface, graphene_nanoribbon
import numpy as np


# Materials Project API key from environment
MP_API_KEY = os.environ.get("MP_API_KEY", None)


def load_structure(structure: str | Path | Atoms) -> Atoms:
    """
    Load an atomic structure from various formats.

    Args:
        structure: One of:
            - ASE Atoms object (returned as-is)
            - Path to a structure file (.cif, .vasp, .xyz, .poscar, etc.)
            - String containing structure data (CIF, XYZ, POSCAR, extxyz)
            - Simple formula for common structures:
                - "Si" -> bulk silicon (diamond)
                - "Cu" -> bulk copper (FCC)
                - "Fe" -> bulk iron (BCC)
                - "graphene" -> monolayer graphene
                - "H2O" -> water molecule
            - Materials Project ID: "mp-149" (requires MP_API_KEY)
            - XYZ + lattice: "xyz:C 0 0 0; C 1.42 0 0|lattice:2.46,0,0,0,4.26,0,0,0,15"
            - Natural text: "Si bulk diamond cubic a = 5.43 angstrom"
              or "cubic cell a=5.43; fractional coordinates: Si 0 0 0; Si 0.25 0.25 0.25"

    Returns:
        ASE Atoms object
    """
    if isinstance(structure, Atoms):
        return structure

    if isinstance(structure, Path):
        structure = str(structure)

    # Check if it's a file path
    if isinstance(structure, str):
        # Check for Materials Project ID (e.g., mp-149, mp-1234)
        if structure.lower().startswith("mp-"):
            return _load_from_materials_project(structure)
        
        # Check for inline XYZ + lattice format
        if "xyz:" in structure.lower() or "|lattice:" in structure.lower():
            return _parse_inline_structure(structure)

        atoms = _parse_natural_language_structure(structure)
        if atoms is not None:
            return atoms
        
        path = Path(structure)
        if path.exists() and path.is_file():
            # Determine format from extension
            suffix = path.suffix.lower()
            format_map = {
                ".cif": "cif",
                ".vasp": "vasp",
                ".poscar": "vasp",
                ".xyz": "xyz",
                ".extxyz": "extxyz",
                ".pdb": "pdb",
                ".json": "json",
                ".xsf": "xsf",
                ".gen": "gen",
            }
            fmt = format_map.get(suffix, None)
            try:
                if fmt:
                    return read(str(path), format=fmt)
                else:
                    return read(str(path))  # Let ASE auto-detect
            except Exception as e:
                raise ValueError(f"Failed to read file {path}: {e}")

        # Check if it's a string containing structure data
        atoms = _parse_structure_string(structure)
        if atoms is not None:
            return atoms

        # Try as a simple formula or named structure
        atoms = _build_from_formula(structure)
        if atoms is not None:
            return atoms

        raise ValueError(
            f"Could not parse structure: '{structure}'. "
            "Provide a file path, structure data, formula (e.g., 'Si', 'graphene'), "
            "or Materials Project ID (e.g., 'mp-149')."
        )

    raise TypeError(f"Expected str, Path, or Atoms, got {type(structure)}")


def _parse_natural_language_structure(structure: str) -> Optional[Atoms]:
    """
    Parse compact natural-language structure descriptions.

    This intentionally handles only low-ambiguity cases. Ambiguous free text
    should still fail loudly rather than silently creating the wrong structure.
    """
    text = structure.strip()
    lower = text.lower()
    if not text or "\n" not in text and not any(
        token in lower for token in (
            "bulk", "cubic", "lattice", "angstrom", "fractional", "crystal",
            "diamond", "fcc", "bcc", "hcp", "rocksalt", "rock salt",
            "zincblende", "zinc blende", " a=", " a =", "cell",
        )
    ):
        return None

    formula = _extract_formula(text)
    a = _extract_lattice_constant(text, "a")
    b = _extract_lattice_constant(text, "b")
    c = _extract_lattice_constant(text, "c")

    structure_type = _infer_structure_type(lower)
    if formula and structure_type:
        try:
            if structure_type == "hcp":
                c_over_a = (c / a) if (a and c) else None
                return bulk(formula, structure_type, a=a, c=a * c_over_a) if c_over_a else bulk(formula, structure_type, a=a)
            if a:
                return bulk(formula, structure_type, a=a)
            return bulk(formula, structure_type)
        except Exception:
            pass

    atoms_data = _extract_atom_coordinate_lines(text)
    if atoms_data and (a or b or c or "lattice" in lower or "cell" in lower):
        a = a or b or c
        b = b or a
        c = c or a
        if not (a and b and c):
            return None
        cell = np.diag([a, b, c])
        symbols = [item[0] for item in atoms_data]
        coords = np.array([item[1] for item in atoms_data], dtype=float)
        coord_mode = _infer_coordinate_mode(lower, coords)
        if coord_mode == "fractional":
            atoms = Atoms(symbols=symbols, scaled_positions=coords, cell=cell, pbc=True)
        else:
            atoms = Atoms(symbols=symbols, positions=coords, cell=cell, pbc=True)
        return atoms

    return None


def _extract_formula(text: str) -> str | None:
    """Return the first plausible chemical formula in free text."""
    skip = {
        "bulk", "diamond", "cubic", "cell", "lattice", "angstrom", "ang", "crystal",
        "fractional", "cartesian", "coordinates", "coord", "structure", "with",
    }
    for token in re.findall(r"\b[A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?\d*)*\b", text):
        if token.lower() not in skip:
            return token
    return None


def _extract_lattice_constant(text: str, name: str) -> float | None:
    """Extract lattice constants like a=5.43 or a = 5.43 angstrom."""
    match = re.search(
        rf"\b{name}\s*(?:=|:|is)?\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)",
        text,
        re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


def _infer_structure_type(lower: str) -> str | None:
    """Map common natural-language crystal names to ASE bulk crystal structures."""
    if "diamond" in lower:
        return "diamond"
    if "zinc blende" in lower or "zincblende" in lower or "sphalerite" in lower:
        return "zincblende"
    if "rock salt" in lower or "rocksalt" in lower or "nacl" in lower:
        return "rocksalt"
    if "body centered" in lower or "body-centred" in lower or "bcc" in lower:
        return "bcc"
    if "face centered" in lower or "face-centred" in lower or "fcc" in lower:
        return "fcc"
    if "hexagonal close" in lower or "hcp" in lower:
        return "hcp"
    if "simple cubic" in lower or " sc " in f" {lower} ":
        return "sc"
    return None


def _extract_atom_coordinate_lines(text: str) -> list[tuple[str, list[float]]]:
    """Extract lines like 'Si 0.0 0.0 0.0' from free text."""
    atoms_data: list[tuple[str, list[float]]] = []
    for raw_line in re.split(r"[\n;]+", text):
        line = raw_line.strip()
        match = re.match(
            r"^([A-Z][a-z]?)\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
            r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
            r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\b",
            line,
        )
        if match:
            atoms_data.append((
                match.group(1),
                [float(match.group(2)), float(match.group(3)), float(match.group(4))],
            ))
    return atoms_data


def _infer_coordinate_mode(lower: str, coords: np.ndarray) -> str:
    """Infer fractional vs Cartesian coordinates for natural-language blocks."""
    if any(word in lower for word in ("fractional", "frac", "crystal", "scaled", "direct")):
        return "fractional"
    if any(word in lower for word in ("cartesian", "cart", "angstrom positions", "xyz")):
        return "cartesian"
    if coords.size and np.all(coords >= -1e-12) and np.all(coords <= 1.0 + 1e-12):
        return "fractional"
    return "cartesian"


def _parse_structure_string(structure: str) -> Optional[Atoms]:
    """Try to parse a string as structure data (CIF, POSCAR, XYZ, extxyz)."""
    
    lines = structure.strip().split('\n')
    
    # Try CIF format
    if "data_" in structure or "_atom_site" in structure or "_cell_" in structure:
        try:
            return read(StringIO(structure), format="cif")
        except Exception:
            pass

    # Try POSCAR/VASP format - look for Direct or Cartesian keywords
    if len(lines) >= 7:
        # Check if lines 3-5 look like lattice vectors (3 floats each)
        try:
            # Check for lattice-like lines
            for i in range(2, 5):
                parts = lines[i].split()
                if len(parts) >= 3:
                    float(parts[0]), float(parts[1]), float(parts[2])
            # Try to read as VASP
            atoms = read(StringIO(structure), format="vasp")
            return atoms
        except Exception:
            pass

    # Try extxyz format (has "Lattice=" in header)
    if "Lattice=" in structure or "Properties=" in structure:
        try:
            return read(StringIO(structure), format="extxyz")
        except Exception:
            pass

    # Try standard XYZ format (natoms, comment, positions)
    # XYZ format: first line is number of atoms, second is comment, rest are positions
    if len(lines) >= 3:
        try:
            first_line = lines[0].strip()
            # Check if first line is just a number
            if first_line.isdigit():
                natoms = int(first_line)
                if natoms > 0 and len(lines) >= natoms + 2:
                    atoms = read(StringIO(structure), format="xyz")
                    # XYZ files don't have a cell, so add vacuum box
                    # Check if cell is defined by looking at pbc or trying to get volume
                    try:
                        vol = atoms.get_volume()
                        if vol < 0.1:  # Essentially zero
                            atoms.center(vacuum=10.0)
                    except Exception:
                        # No cell defined, add vacuum
                        atoms.center(vacuum=10.0)
                    return atoms
        except Exception:
            pass

    return None


def _parse_inline_structure(structure: str) -> Atoms:
    """
    Parse inline XYZ + lattice format.
    
    Format: "xyz:SYMBOL X Y Z; SYMBOL X Y Z|lattice:a1,a2,a3,b1,b2,b3,c1,c2,c3"
    
    Examples:
        "xyz:C 0 0 0; C 1.42 0 0|lattice:2.46,0,0,0,4.26,0,0,0,15"
        "xyz:Si 0 0 0; Si 1.36 1.36 1.36|lattice:5.43,0,0,0,5.43,0,0,0,5.43"
    """
    structure = structure.strip()
    
    # Parse lattice
    lattice_match = re.search(r'\|?lattice:([0-9.,\-\s]+)', structure, re.IGNORECASE)
    if lattice_match:
        lattice_str = lattice_match.group(1)
        lattice_values = [float(x.strip()) for x in lattice_str.split(',')]
        if len(lattice_values) == 9:
            cell = np.array(lattice_values).reshape(3, 3)
        elif len(lattice_values) == 3:
            # Just a, b, c - assume orthorhombic
            cell = np.diag(lattice_values)
        else:
            raise ValueError(f"Lattice must have 3 or 9 values, got {len(lattice_values)}")
    else:
        cell = None
    
    # Parse XYZ positions
    xyz_match = re.search(r'xyz:([^|]+)', structure, re.IGNORECASE)
    if not xyz_match:
        raise ValueError("No 'xyz:' section found in inline structure")
    
    xyz_str = xyz_match.group(1).strip()
    atoms_data = xyz_str.split(';')
    
    symbols = []
    positions = []
    for atom_str in atoms_data:
        parts = atom_str.strip().split()
        if len(parts) >= 4:
            symbols.append(parts[0])
            positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
    
    if not symbols:
        raise ValueError("No valid atoms found in inline structure")
    
    atoms = Atoms(symbols=symbols, positions=positions)
    
    if cell is not None:
        atoms.set_cell(cell)
        atoms.set_pbc([True, True, True])
    else:
        atoms.center(vacuum=10.0)
    
    return atoms


def _load_from_materials_project(mp_id: str) -> Atoms:
    """
    Load structure from Materials Project using their API.
    
    Requires MP_API_KEY environment variable or mp_api package.
    
    Args:
        mp_id: Materials Project ID (e.g., "mp-149" for silicon)
    
    Returns:
        ASE Atoms object
    """
    api_key = MP_API_KEY
    
    if api_key is None:
        raise ValueError(
            "Materials Project API key not found. "
            "Set MP_API_KEY environment variable or use: export MP_API_KEY='your_key'"
        )
    
    try:
        from mp_api.client import MPRester
        
        with MPRester(api_key) as mpr:
            # Get the structure
            structure = mpr.get_structure_by_material_id(mp_id)
            
            # Convert pymatgen Structure to ASE Atoms
            return _pymatgen_to_ase(structure)
            
    except ImportError:
        # Fallback to direct API call
        return _load_from_mp_rest_api(mp_id, api_key)


def _load_from_mp_rest_api(mp_id: str, api_key: str) -> Atoms:
    """Load from Materials Project using REST API directly."""
    import urllib.request
    import json
    
    url = f"https://api.materialsproject.org/materials/core/?material_ids={mp_id}&_fields=structure"
    
    headers = {
        "X-API-KEY": api_key,
        "accept": "application/json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        raise ValueError(f"Failed to fetch from Materials Project: {e}")
    
    if not data.get("data"):
        raise ValueError(f"No structure found for {mp_id}")
    
    # Parse the structure from the response
    struct_data = data["data"][0]["structure"]
    
    # Extract lattice and sites
    lattice = struct_data["lattice"]["matrix"]
    cell = np.array(lattice)
    
    symbols = []
    positions = []
    for site in struct_data["sites"]:
        symbols.append(site["species"][0]["element"])
        positions.append(site["xyz"])
    
    atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    return atoms


def _pymatgen_to_ase(structure) -> Atoms:
    """Convert pymatgen Structure to ASE Atoms."""
    from pymatgen.io.ase import AseAtomsAdaptor
    return AseAtomsAdaptor.get_atoms(structure)


def _build_from_formula(formula: str) -> Optional[Atoms]:
    """
    Build structure from a simple formula or name.

    Supports:
    - Single elements with known crystal structures
    - 2D materials (graphene, hBN, MoS2)
    - Simple molecules
    - Named structures
    """
    formula = formula.strip()
    formula_lower = formula.lower()

    # =========== 2D Materials ===========
    if formula_lower in ("graphene", "graphene_monolayer", "c_graphene"):
        return _build_graphene()
    
    if formula_lower in ("hbn", "bn", "hexagonal_bn", "boron_nitride"):
        return _build_hbn()
    
    if formula_lower in ("mos2", "mos2_monolayer"):
        return _build_mos2()
    
    if formula_lower in ("ws2", "ws2_monolayer"):
        return _build_ws2()
    
    if formula_lower in ("black_phosphorus", "phosphorene", "bp"):
        return _build_phosphorene()

    # =========== Bulk Structures ===========
    bulk_structures = {
        # FCC metals
        "Al": ("fcc", 4.05),
        "Cu": ("fcc", 3.615),
        "Ag": ("fcc", 4.09),
        "Au": ("fcc", 4.08),
        "Ni": ("fcc", 3.52),
        "Pd": ("fcc", 3.89),
        "Pt": ("fcc", 3.92),
        "Pb": ("fcc", 4.95),
        "Ca": ("fcc", 5.58),
        "Sr": ("fcc", 6.08),
        "Rh": ("fcc", 3.80),
        "Ir": ("fcc", 3.84),
        # BCC metals
        "Fe": ("bcc", 2.87),
        "Cr": ("bcc", 2.91),
        "Mo": ("bcc", 3.15),
        "W": ("bcc", 3.16),
        "V": ("bcc", 3.03),
        "Nb": ("bcc", 3.30),
        "Ta": ("bcc", 3.31),
        "K": ("bcc", 5.23),
        "Na": ("bcc", 4.29),
        "Li": ("bcc", 3.49),
        "Ba": ("bcc", 5.02),
        "Cs": ("bcc", 6.14),
        "Rb": ("bcc", 5.59),
        # Diamond structure
        "Si": ("diamond", 5.43),
        "Ge": ("diamond", 5.66),
        "C": ("diamond", 3.57),  # Diamond carbon
        "Sn": ("diamond", 6.49),  # alpha-Sn
        # HCP metals
        "Mg": ("hcp", 3.21, 1.624),
        "Ti": ("hcp", 2.95, 1.588),
        "Zn": ("hcp", 2.66, 1.856),
        "Co": ("hcp", 2.51, 1.622),
        "Zr": ("hcp", 3.23, 1.593),
        "Hf": ("hcp", 3.19, 1.582),
        "Cd": ("hcp", 2.98, 1.886),
        "Be": ("hcp", 2.29, 1.567),
        "Sc": ("hcp", 3.31, 1.594),
        "Y": ("hcp", 3.65, 1.571),
        "Ru": ("hcp", 2.71, 1.584),
        "Os": ("hcp", 2.73, 1.579),
        "Re": ("hcp", 2.76, 1.615),
        "Tc": ("hcp", 2.74, 1.604),
        # Rocksalt
        "NaCl": ("rocksalt", 5.64),
        "MgO": ("rocksalt", 4.21),
        "LiF": ("rocksalt", 4.03),
        "NaF": ("rocksalt", 4.62),
        "KCl": ("rocksalt", 6.29),
        "CaO": ("rocksalt", 4.81),
        "BaO": ("rocksalt", 5.52),
        "TiO": ("rocksalt", 4.18),
        "VO": ("rocksalt", 4.06),
        "MnO": ("rocksalt", 4.44),
        "FeO": ("rocksalt", 4.31),
        "CoO": ("rocksalt", 4.26),
        "NiO": ("rocksalt", 4.18),
        # Zinc blende
        "GaAs": ("zincblende", 5.65),
        "ZnS": ("zincblende", 5.41),
        "SiC": ("zincblende", 4.36),
        "AlAs": ("zincblende", 5.66),
        "GaP": ("zincblende", 5.45),
        "InP": ("zincblende", 5.87),
        "InAs": ("zincblende", 6.06),
        "InSb": ("zincblende", 6.48),
        "GaSb": ("zincblende", 6.10),
        "AlSb": ("zincblende", 6.14),
        "ZnSe": ("zincblende", 5.67),
        "ZnTe": ("zincblende", 6.10),
        "CdS": ("zincblende", 5.82),
        "CdSe": ("zincblende", 6.05),
        "CdTe": ("zincblende", 6.48),
        "HgTe": ("zincblende", 6.46),
        # Wurtzite
        "GaN": ("wurtzite", 3.19, 1.627),
        "AlN": ("wurtzite", 3.11, 1.600),
        "InN": ("wurtzite", 3.54, 1.612),
        "ZnO": ("wurtzite", 3.25, 1.602),
        # Cesium chloride structure
        "CsCl": ("cesiumchloride", 4.12),
        # Simple cubic
        "Po": ("sc", 3.35),
    }

    if formula in bulk_structures:
        params = bulk_structures[formula]
        if len(params) == 2:
            structure_type, a = params
            return bulk(formula, structure_type, a=a)
        else:
            structure_type, a, c_over_a = params
            return bulk(formula, structure_type, a=a, c=a * c_over_a)

    # =========== Molecules ===========
    known_molecules = [
        "H2", "N2", "O2", "F2", "Cl2", "Br2", "I2",
        "CO", "CO2", "NO", "NO2", "N2O", "SO2", "SO3",
        "H2O", "H2O2", "NH3", "PH3", "H2S",
        "CH4", "C2H2", "C2H4", "C2H6", "C3H8", "C6H6",
        "CH3OH", "C2H5OH", "HCOOH", "CH3CHO",
        "HF", "HCl", "HBr", "HI", "HCN",
        "O3", "N2H4", "CH3NH2",
    ]

    if formula in known_molecules:
        try:
            mol = molecule(formula)
            # Add vacuum box around molecule
            mol.center(vacuum=10.0)
            return mol
        except Exception:
            pass

    # =========== Perovskites (ABO3) ===========
    perovskites = {
        "SrTiO3": 3.905,
        "BaTiO3": 4.00,
        "PbTiO3": 3.97,
        "KNbO3": 4.02,
        "LaMnO3": 3.88,
        "LaAlO3": 3.79,
        "SrVO3": 3.84,
        "CaTiO3": 3.82,
    }
    
    if formula in perovskites:
        return _build_perovskite(formula, perovskites[formula])

    return None


def _build_graphene(vacuum: float = 15.0) -> Atoms:
    """
    Build monolayer graphene primitive cell.
    
    Uses experimental lattice constant a = 2.46 Å.
    Returns a 2-atom primitive cell with vacuum in z-direction.
    """
    a = 2.46  # Lattice constant in Angstrom
    
    # Primitive cell vectors for graphene
    cell = np.array([
        [a, 0, 0],
        [a/2, a * np.sqrt(3)/2, 0],
        [0, 0, vacuum]
    ])
    
    # Two carbon atoms in the primitive cell
    positions = np.array([
        [0, 0, vacuum/2],
        [a/2, a/(2*np.sqrt(3)), vacuum/2]
    ])
    
    atoms = Atoms('C2', positions=positions, cell=cell, pbc=[True, True, False])
    return atoms


def _build_hbn(vacuum: float = 15.0) -> Atoms:
    """
    Build monolayer hexagonal boron nitride (h-BN).
    
    Uses lattice constant a = 2.50 Å.
    """
    a = 2.50
    
    cell = np.array([
        [a, 0, 0],
        [a/2, a * np.sqrt(3)/2, 0],
        [0, 0, vacuum]
    ])
    
    positions = np.array([
        [0, 0, vacuum/2],
        [a/2, a/(2*np.sqrt(3)), vacuum/2]
    ])
    
    atoms = Atoms('BN', positions=positions, cell=cell, pbc=[True, True, False])
    return atoms


def _build_mos2(vacuum: float = 15.0) -> Atoms:
    """
    Build monolayer MoS2 (1H phase).
    
    Uses lattice constant a = 3.16 Å, S-Mo-S height = 3.13 Å.
    """
    a = 3.16
    h = 1.565  # Half the S-Mo-S distance
    
    cell = np.array([
        [a, 0, 0],
        [a/2, a * np.sqrt(3)/2, 0],
        [0, 0, vacuum]
    ])
    
    # Mo at center, S above and below
    positions = np.array([
        [0, 0, vacuum/2],                    # Mo
        [a/2, a/(2*np.sqrt(3)), vacuum/2 + h],  # S above
        [a/2, a/(2*np.sqrt(3)), vacuum/2 - h],  # S below
    ])
    
    atoms = Atoms('MoS2', positions=positions, cell=cell, pbc=[True, True, False])
    return atoms


def _build_ws2(vacuum: float = 15.0) -> Atoms:
    """Build monolayer WS2 (1H phase)."""
    a = 3.18
    h = 1.57
    
    cell = np.array([
        [a, 0, 0],
        [a/2, a * np.sqrt(3)/2, 0],
        [0, 0, vacuum]
    ])
    
    positions = np.array([
        [0, 0, vacuum/2],
        [a/2, a/(2*np.sqrt(3)), vacuum/2 + h],
        [a/2, a/(2*np.sqrt(3)), vacuum/2 - h],
    ])
    
    atoms = Atoms('WS2', positions=positions, cell=cell, pbc=[True, True, False])
    return atoms


def _build_phosphorene(vacuum: float = 15.0) -> Atoms:
    """
    Build monolayer black phosphorus (phosphorene).
    
    Puckered structure with 4 atoms per unit cell.
    """
    a = 4.58  # in-plane lattice constant (zigzag direction)
    b = 3.32  # in-plane lattice constant (armchair direction)
    d1 = 0.5  # lower layer offset
    d2 = 2.1  # upper layer z
    
    cell = np.array([
        [a, 0, 0],
        [0, b, 0],
        [0, 0, vacuum]
    ])
    
    z0 = vacuum/2
    positions = np.array([
        [0.0, 0.0, z0],
        [0.0, b/2, z0 + d1],
        [a/2, 0.0, z0 + d2],
        [a/2, b/2, z0 + d2 - d1],
    ])
    
    atoms = Atoms('P4', positions=positions, cell=cell, pbc=[True, True, False])
    return atoms


def _build_perovskite(formula: str, a: float) -> Atoms:
    """
    Build cubic perovskite ABO3 structure.
    
    A at corners, B at center, O at face centers.
    """
    # Parse ABO3 formula to get elements
    # Simple parsing for common perovskites
    element_map = {
        "SrTiO3": ("Sr", "Ti", "O"),
        "BaTiO3": ("Ba", "Ti", "O"),
        "PbTiO3": ("Pb", "Ti", "O"),
        "KNbO3": ("K", "Nb", "O"),
        "LaMnO3": ("La", "Mn", "O"),
        "LaAlO3": ("La", "Al", "O"),
        "SrVO3": ("Sr", "V", "O"),
        "CaTiO3": ("Ca", "Ti", "O"),
    }
    
    if formula not in element_map:
        raise ValueError(f"Unknown perovskite: {formula}")
    
    A, B, O = element_map[formula]
    
    cell = np.array([
        [a, 0, 0],
        [0, a, 0],
        [0, 0, a]
    ])
    
    # A at corner, B at center, O at face centers
    positions = np.array([
        [0, 0, 0],           # A
        [a/2, a/2, a/2],     # B
        [a/2, a/2, 0],       # O
        [a/2, 0, a/2],       # O
        [0, a/2, a/2],       # O
    ])
    
    symbols = [A, B, O, O, O]
    
    atoms = Atoms(symbols=symbols, positions=positions, cell=cell, pbc=True)
    return atoms


def get_kpath(
    atoms: Atoms,
    npoints: int = 100,
) -> tuple[np.ndarray, dict[str, float]]:
    """
    Generate a high-symmetry k-path for band structure calculations.

    Args:
        atoms: ASE Atoms object
        npoints: Total number of k-points along the path

    Returns:
        kpts: Array of k-points in crystal coordinates
        special_points: Dict mapping label to position along path (0 to 1)
    """
    from ase.dft.kpoints import bandpath

    # Get the band path
    path = atoms.cell.bandpath(npoints=npoints)

    return path.kpts, path.special_points


def get_kpoints_grid(
    atoms: Atoms,
    kspacing: float | None = None,
    density: str = "medium",
) -> list[int]:
    """
    Generate Monkhorst-Pack k-point grid based on cell size.
    
    Uses the rule: smaller cells need more k-points.
    Prefers odd numbers (1, 3, 5, 7, 9, 11, ...) for better symmetry sampling.
    
    Approximate mapping (per lattice vector):
        Cell size ~3 Å  → 11-13 k-points
        Cell size ~4 Å  → 9-11 k-points  
        Cell size ~5 Å  → 7-9 k-points
        Cell size ~8 Å  → 5-7 k-points
        Cell size ~10 Å → 3-5 k-points
        Cell size ~15 Å → 3 k-points
        Cell size >20 Å → 1 k-points (Gamma)
    
    Args:
        atoms: ASE Atoms object
        kspacing: Optional explicit k-point spacing in 1/Angstrom.
                  If None, uses cell-size based automatic selection.
        density: K-point density preset if kspacing is None:
                 - "low": coarse grid for quick tests
                 - "medium": balanced (default, good for most calculations)
                 - "high": dense grid for accurate calculations
    
    Returns:
        [n1, n2, n3] k-point grid with preferred odd numbers
    """
    # Preferred k-point values (odd numbers for gamma-centered grids)
    PREFERRED_KPTS = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21]
    
    # Target k-points * cell_length product (in Å)
    # These are tuned so that:
    # - 4 Å cell → ~9-11 k-points (medium)
    # - 8 Å cell → ~5-7 k-points (medium)
    # - 16 Å cell → ~3 k-points (medium)
    density_factors = {
        "low": 25,      # e.g., 4 Å cell → 6 → snaps to 7
        "medium": 40,   # e.g., 4 Å cell → 10 → snaps to 9 or 11
        "high": 60,     # e.g., 4 Å cell → 15 → snaps to 15
    }
    
    cell = atoms.get_cell()
    pbc = atoms.get_pbc()
    
    # Calculate lattice vector lengths
    lengths = np.linalg.norm(cell, axis=1)
    
    kpts = []
    for i, length in enumerate(lengths):
        if not pbc[i]:
            # Non-periodic direction: always Gamma only
            kpts.append(1)
            continue
            
        if kspacing is not None:
            # Use explicit spacing in reciprocal space
            # kspacing is in 1/Angstrom, reciprocal lattice spacing is 2π/a
            # n ≈ (2π/a) / kspacing = 2π / (a * kspacing)
            # But commonly, kspacing=0.04 means ~0.04 Å⁻¹ spacing
            # So for cell=4Å, reciprocal=1.57 Å⁻¹, n = 1.57/0.04 ≈ 39 (too many!)
            # Better interpretation: n * kspacing ≈ 2π/a
            # Simpler: use kspacing as target density, n = ceiling(1/(a*kspacing))
            n = max(1, int(np.ceil(1.0 / (length * kspacing))))
        else:
            # Use cell-size based automatic selection
            factor = density_factors.get(density, density_factors["medium"])
            n = max(1, int(np.round(factor / length)))
        
        # Snap to nearest preferred odd number
        n = _snap_to_preferred(n, PREFERRED_KPTS)
        kpts.append(n)
    
    return kpts


def _snap_to_preferred(n: int, preferred: list[int]) -> int:
    """Snap a k-point value to the nearest preferred value."""
    if n <= 1:
        return 1
    if n >= preferred[-1]:
        return preferred[-1]
    
    # Find closest preferred value
    best = preferred[0]
    min_diff = abs(n - best)
    
    for p in preferred:
        diff = abs(n - p)
        if diff < min_diff:
            min_diff = diff
            best = p
        elif diff == min_diff and p > best:
            # Prefer larger value if tied (more accurate)
            best = p
    
    return best


def get_default_kpoints(atoms: Atoms) -> list[int]:
    """
    Get default k-points for a structure.
    
    Simple helper that returns sensible defaults:
    - Molecules/slabs with vacuum: Gamma (1x1x1) in vacuum direction
    - Small cells (<5 Å): Dense grid (11-15)
    - Medium cells (5-10 Å): Medium grid (5-9)
    - Large cells (>10 Å): Sparse grid (1-5)
    
    Args:
        atoms: ASE Atoms object
        
    Returns:
        [n1, n2, n3] k-point grid
    """
    return get_kpoints_grid(atoms, density="medium")


def atoms_to_dict(atoms: Atoms) -> dict[str, Any]:
    """Convert Atoms to a serializable dictionary."""
    return {
        "symbols": atoms.get_chemical_symbols(),
        "positions": atoms.get_positions().tolist(),
        "cell": atoms.get_cell().tolist(),
        "pbc": atoms.get_pbc().tolist(),
        "formula": atoms.get_chemical_formula(),
        "n_atoms": len(atoms),
    }
