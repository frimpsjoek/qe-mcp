"""
Utility tools for QE MCP server.

Helper tools for structure loading, validation, Materials Project access, etc.
"""

from pathlib import Path
from typing import Any
import os

from qe_mcp.config import QEConfig
from qe_mcp.core.structures import load_structure, get_kpath, get_kpoints_grid, atoms_to_dict
from qe_mcp.core.pseudopotentials import SG15Library


def load_structure_tool(structure: str) -> dict[str, Any]:
    """
    Load and validate an atomic structure.

    Accepts various formats:
    - File path to CIF, POSCAR, XYZ, VASP, etc.
    - Structure data as a string (CIF, POSCAR, XYZ, extxyz)
    - Simple formula like "Si", "Cu", "GaAs"
    - 2D materials: "graphene", "hBN", "MoS2", "WS2", "phosphorene"
    - Perovskites: "SrTiO3", "BaTiO3", etc.
    - Materials Project ID: "mp-149" (requires MP_API_KEY)
    - Inline format: "xyz:C 0 0 0; C 1.42 0 0|lattice:2.46,0,0,0,4.26,0,0,0,15"

    Args:
        structure: Structure specification

    Returns:
        Dictionary with structure information:
        - formula: Chemical formula
        - n_atoms: Number of atoms
        - symbols: List of element symbols
        - cell: Unit cell as 3x3 matrix (Angstrom)
        - volume: Cell volume (Å³)
        - positions: Atomic positions (Angstrom)
        - pbc: Periodic boundary conditions
    """
    try:
        atoms = load_structure(structure)
        info = atoms_to_dict(atoms)
        info["volume_angstrom3"] = atoms.get_volume()
        info["success"] = True
        return info
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def search_materials_project(
    query: str,
    fields: list[str] | None = None,
    num_results: int = 10,
) -> dict[str, Any]:
    """
    Search Materials Project database for structures.
    
    Requires MP_API_KEY environment variable.
    
    Args:
        query: Search query. Can be:
            - Formula: "Fe2O3", "Si", "GaAs"
            - Element(s): "Fe-O" (materials containing Fe and O)
            - Chemsys: "Li-Fe-O" (all materials in Li-Fe-O chemical space)
        fields: Optional list of fields to return. Default includes common fields.
        num_results: Maximum number of results (default: 10)
    
    Returns:
        Dictionary with:
        - success: Boolean
        - results: List of matching materials with mp_id, formula, etc.
        - hint: Usage hint if API key missing
    
    Examples:
        search_materials_project("Si")           # Find silicon structures
        search_materials_project("Fe-O")         # Iron oxides
        search_materials_project("Li-Fe-P-O")    # Battery materials
    """
    api_key = os.environ.get("MP_API_KEY")
    
    if not api_key:
        return {
            "success": False,
            "error": "MP_API_KEY not set",
            "hint": "Set MP_API_KEY environment variable with your Materials Project API key. "
                    "Get one at: https://materialsproject.org/api"
        }
    
    if fields is None:
        fields = [
            "material_id",
            "formula_pretty",
            "energy_per_atom",
            "formation_energy_per_atom",
            "band_gap",
            "is_metal",
            "is_stable",
            "symmetry",
            "nsites",
        ]
    
    try:
        from mp_api.client import MPRester
        
        with MPRester(api_key) as mpr:
            # Determine search type
            if "-" in query:
                # Chemical system search
                elements = query.split("-")
                docs = mpr.materials.summary.search(
                    chemsys=elements,
                    fields=fields,
                    num_chunks=1,
                )[:num_results]
            else:
                # Formula search
                docs = mpr.materials.summary.search(
                    formula=query,
                    fields=fields,
                    num_chunks=1,
                )[:num_results]
            
            results = []
            for doc in docs:
                result = {"material_id": str(doc.material_id)}
                for field in fields:
                    if field != "material_id" and hasattr(doc, field):
                        val = getattr(doc, field)
                        if hasattr(val, "dict"):
                            result[field] = val.dict() if hasattr(val, "dict") else str(val)
                        else:
                            result[field] = val
                results.append(result)
            
            return {
                "success": True,
                "query": query,
                "n_results": len(results),
                "results": results,
                "hint": "Use load_structure with the material_id (e.g., 'mp-149') to load a structure"
            }
            
    except ImportError:
        return _search_mp_rest_api(query, api_key, num_results)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def _search_mp_rest_api(query: str, api_key: str, num_results: int) -> dict[str, Any]:
    """Search Materials Project using REST API directly."""
    import urllib.request
    import urllib.parse
    import json
    
    # Determine if it's a chemical system or formula
    if "-" in query:
        chemsys = query
        url = f"https://api.materialsproject.org/materials/core/?chemsys={chemsys}&_limit={num_results}"
    else:
        url = f"https://api.materialsproject.org/materials/core/?formula={query}&_limit={num_results}"
    
    url += "&_fields=material_id,formula_pretty,energy_per_atom,formation_energy_per_atom,band_gap,is_metal,nsites"
    
    headers = {
        "X-API-KEY": api_key,
        "accept": "application/json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        return {
            "success": False,
            "error": f"API request failed: {e}"
        }
    
    results = []
    for item in data.get("data", []):
        results.append({
            "material_id": item.get("material_id"),
            "formula": item.get("formula_pretty"),
            "energy_per_atom_eV": item.get("energy_per_atom"),
            "formation_energy_eV": item.get("formation_energy_per_atom"),
            "band_gap_eV": item.get("band_gap"),
            "is_metal": item.get("is_metal"),
            "n_sites": item.get("nsites"),
        })
    
    return {
        "success": True,
        "query": query,
        "n_results": len(results),
        "results": results,
        "hint": "Use load_structure with the material_id (e.g., 'mp-149') to load a structure"
    }


def get_mp_structure(mp_id: str) -> dict[str, Any]:
    """
    Get structure from Materials Project by ID.
    
    This is a convenience wrapper that loads and returns structure info.
    
    Args:
        mp_id: Materials Project ID (e.g., "mp-149" for silicon)
    
    Returns:
        Dictionary with structure information including cell, positions, etc.
    
    Examples:
        get_mp_structure("mp-149")    # Silicon
        get_mp_structure("mp-19017")  # Fe2O3
    """
    return load_structure_tool(mp_id)


def get_kpath_tool(
    structure: str,
    npoints: int = 100,
) -> dict[str, Any]:
    """
    Get high-symmetry k-path for band structure calculation.

    Automatically determines the appropriate path based on
    the crystal structure's Bravais lattice.

    Args:
        structure: Atomic structure (file, string, or formula)
        npoints: Number of k-points along the path

    Returns:
        Dictionary with:
        - kpoints: List of k-points in crystal coordinates
        - special_points: Dict mapping labels to k-point indices
        - path_labels: String representation of the path (e.g., "G-X-M-G")
    """
    try:
        atoms = load_structure(structure)
        kpts, special_points = get_kpath(atoms, npoints=npoints)

        # Create path label string
        labels = sorted(special_points.items(), key=lambda x: x[1])
        path_str = "-".join(label for label, _ in labels)

        return {
            "success": True,
            "n_kpoints": len(kpts),
            "special_points": special_points,
            "path_labels": path_str,
            "kpoints": kpts.tolist(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def suggest_kpoints(
    structure: str,
    density: str = "medium",
    kspacing: float | None = None,
) -> dict[str, Any]:
    """
    Suggest Monkhorst-Pack k-point grid for a structure.
    
    Uses cell-size based automatic selection with preferred odd numbers
    (3, 5, 7, 9, 11, 13, 15, 17, 19, 21) for better symmetry sampling.

    Args:
        structure: Atomic structure
        density: K-point density preset:
            - "low": Coarse grid (quick tests)
            - "medium": Balanced (default, production)
            - "high": Dense grid (accurate)
        kspacing: Optional explicit k-point spacing in 1/Angstrom
            - 0.02: Very dense (accurate, slow)
            - 0.04: Dense (good for production)
            - 0.06: Medium (reasonable for testing)
            - 0.10: Coarse (quick tests only)

    Returns:
        Dictionary with suggested k-grid and reasoning
    """
    try:
        atoms = load_structure(structure)
        
        # Get cell lengths for context
        cell = atoms.get_cell()
        lengths = [f"{l:.2f}" for l in [
            float((cell[0] ** 2).sum() ** 0.5),
            float((cell[1] ** 2).sum() ** 0.5),
            float((cell[2] ** 2).sum() ** 0.5),
        ]]
        
        if kspacing is not None:
            kpts = get_kpoints_grid(atoms, kspacing=kspacing)
            method = f"kspacing={kspacing} 1/Å"
        else:
            kpts = get_kpoints_grid(atoms, density=density)
            method = f"density='{density}'"

        # Estimate total k-points in IBZ (rough)
        total_kpts = kpts[0] * kpts[1] * kpts[2]

        return {
            "success": True,
            "kpoints": kpts,
            "total_kpoints_approx": total_kpts,
            "method": method,
            "cell_lengths_angstrom": lengths,
            "recommendation": (
                f"Suggested k-grid: [{kpts[0]}, {kpts[1]}, {kpts[2]}] "
                f"for cell lengths [{lengths[0]}, {lengths[1]}, {lengths[2]}] Å. "
                f"Approx. {total_kpts} k-points before symmetry reduction."
            ),
            "note": "Uses odd numbers (3,5,7,9,11,...) for gamma-centered grids.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def list_pseudopotentials() -> dict[str, Any]:
    """
    List all available SG15 ONCV pseudopotentials.

    Returns:
        Dictionary with:
        - elements: List of available elements
        - n_elements: Number of elements
        - library: Name of pseudopotential library
        - details: Dict with element -> {filename, ecutwfc, ecutrho}
    """
    try:
        config = QEConfig.from_environment()
        pseudo_lib = SG15Library(config.pseudo_dir)

        elements = pseudo_lib.list_available()
        details = {}
        for el in elements:
            info = pseudo_lib.get(el)
            details[el] = {
                "filename": info.filename,
                "ecutwfc_Ry": info.ecutwfc_hint,
                "ecutrho_Ry": info.ecutrho_hint,
            }

        return {
            "success": True,
            "library": "SG15 ONCV",
            "n_elements": len(elements),
            "elements": elements,
            "details": details,
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e),
            "hint": "Run: python scripts/download_pseudos.py",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def validate_structure(structure: str) -> dict[str, Any]:
    """
    Validate a structure and check for common issues.

    Checks:
    - Structure can be loaded
    - All elements have pseudopotentials
    - Reasonable interatomic distances
    - Properly defined unit cell

    Args:
        structure: Structure to validate

    Returns:
        Dictionary with validation results and warnings
    """
    warnings = []
    errors = []

    try:
        atoms = load_structure(structure)
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to load structure: {e}"],
            "warnings": [],
        }

    # Check pseudopotentials
    try:
        config = QEConfig.from_environment()
        pseudo_lib = SG15Library(config.pseudo_dir)
        elements = list(set(atoms.get_chemical_symbols()))

        for el in elements:
            try:
                pseudo_lib.get(el)
            except ValueError:
                errors.append(f"No pseudopotential for element: {el}")
    except FileNotFoundError:
        warnings.append("Pseudopotential library not found - cannot validate elements")

    # Check cell
    cell = atoms.get_cell()
    volume = atoms.get_volume()

    if volume < 1.0:
        errors.append(f"Cell volume too small: {volume:.2f} Å³")
    elif volume < 10.0:
        warnings.append(f"Cell volume is small: {volume:.2f} Å³")

    # Check for overlapping atoms
    if len(atoms) > 1:
        from ase.geometry import get_distances
        import numpy as np
        positions = atoms.get_positions()
        D, D_len = get_distances(positions, cell=cell, pbc=atoms.get_pbc())

        # D_len is the distance matrix (n x n)
        # Find minimum distance excluding diagonal
        n = len(atoms)
        min_dist = float('inf')
        for i in range(n):
            for j in range(i + 1, n):
                dist = float(D_len[i, j])
                if dist < min_dist:
                    min_dist = dist

        if min_dist < 0.5:
            errors.append(f"Atoms too close: minimum distance = {min_dist:.2f} Å")
        elif min_dist < 1.0:
            warnings.append(f"Some atoms are very close: minimum distance = {min_dist:.2f} Å")

    # Suggest cutoffs
    try:
        ecutwfc, ecutrho = pseudo_lib.get_recommended_cutoffs(elements)
        recommendations = {
            "ecutwfc_Ry": ecutwfc,
            "ecutrho_Ry": ecutrho,
            "kpoints": get_kpoints_grid(atoms),
        }
    except Exception:
        recommendations = None

    return {
        "valid": len(errors) == 0,
        "formula": atoms.get_chemical_formula(),
        "n_atoms": len(atoms),
        "volume_angstrom3": volume,
        "errors": errors,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def get_system_status() -> dict[str, Any]:
    """
    Get QE MCP server status and configuration.

    Returns information about:
    - Docker/local runner availability
    - Pseudopotential library status
    - Work directory
    - Configuration settings
    """
    config = QEConfig.from_environment()

    requested_runner = os.environ.get(
        "QE_RUNNER", "docker" if config.use_docker else "local"
    )
    if requested_runner in ("polaris", "hpc"):
        requested_runner = "globus"

    status = {
        "config": {
            "use_docker": config.use_docker,
            "docker_image": config.docker_image,
            "nprocs": config.nprocs,
            "workdir": str(config.workdir),
            "pseudo_dir": str(config.pseudo_dir),
            "runner": requested_runner,
        }
    }

    # Check runner
    try:
        from qe_mcp.core.runner import get_runner
        runner = get_runner(config)
        status["runner"] = {
            "available": True,
            "type": runner.__class__.__name__,
            "requested": requested_runner,
        }
    except Exception as e:
        status["runner"] = {
            "available": False,
            "error": str(e),
        }

    # Check pseudopotentials
    try:
        pseudo_lib = SG15Library(config.pseudo_dir)
        status["pseudopotentials"] = {
            "available": True,
            "n_elements": len(pseudo_lib.list_available()),
            "library": "SG15 ONCV",
        }
    except Exception as e:
        status["pseudopotentials"] = {
            "available": False,
            "error": str(e),
        }

    return status
