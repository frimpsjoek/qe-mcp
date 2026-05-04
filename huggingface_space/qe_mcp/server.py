"""
Quantum ESPRESSO MCP Server.

A Model Context Protocol server for running DFT calculations
using Quantum ESPRESSO with SG15 ONCV pseudopotentials.
"""

from mcp.server.fastmcp import FastMCP

from qe_mcp.tools.calculations import run_scf, run_relax, run_vc_relax
from qe_mcp.tools.workflows import (
    workflow_bandstructure,
    workflow_dos,
    workflow_relax_and_scf,
)
from qe_mcp.tools.postprocessing import run_bands, run_dos, run_pdos
from qe_mcp.tools.utilities import (
    load_structure_tool,
    get_kpath_tool,
    suggest_kpoints,
    list_pseudopotentials,
    validate_structure,
    get_system_status,
    search_materials_project,
    get_mp_structure,
)
from qe_mcp.tools.data_access import (
    read_bands_gnu,
    read_dos_dat,
    read_pdos_dat,
    list_calculation_files,
)
from qe_mcp.resources import list_resources, get_resource, RESOURCES
from qe_mcp.prompts import list_prompts, get_prompt, PROMPTS

# Create MCP server
mcp = FastMCP("quantum-espresso")

# =============================================================================
# Core Calculation Tools
# =============================================================================


def _parse_kpoints(kpoints_str: str | None) -> list[int] | None:
    """Parse k-points from string like '8,8,8' or 'gamma' or 'auto'."""
    if kpoints_str is None or kpoints_str.strip() == "":
        return None
    kpoints_str = kpoints_str.strip().lower()
    if kpoints_str in ("auto", "none", ""):
        return None
    if kpoints_str == "gamma":
        return [1, 1, 1]
    # Parse "8,8,8" or "8 8 8" format
    parts = kpoints_str.replace(",", " ").split()
    if len(parts) == 3:
        return [int(p) for p in parts]
    elif len(parts) == 1:
        k = int(parts[0])
        return [k, k, k]
    return None


@mcp.tool()
def qe_run_scf(
    structure: str,
    kpoints: str = "auto",
    ecutwfc: float | None = None,
    conv_thr: float | None = None,
    degauss: float | None = None,
    mixing_beta: float | None = None,
    spin_polarized: bool | None = None,
) -> dict:
    """
    Run a self-consistent field (SCF) DFT calculation.

    Computes ground-state electron density and total energy.
    
    ALL PARAMETERS EXCEPT 'structure' ARE OPTIONAL AND AUTO-DETECTED.

    Args:
        structure: Atomic structure - formula ("Si", "Fe", "GaAs"), file path, or CIF/POSCAR string
        kpoints: K-point grid. Options: "auto" (default), "gamma", "8,8,8", or "12" for 12x12x12
        ecutwfc: Plane-wave cutoff in Ry (auto-detected from pseudopotentials if not set)
        conv_thr: SCF convergence threshold (default: 1e-6 Ry). Use 1e-8 for high accuracy.
        degauss: Smearing width in Ry (default: 0.02). Smaller for semiconductors, larger for metals.
        mixing_beta: Charge mixing parameter (default: 0.7). Reduce to 0.3-0.4 for difficult convergence.
        spin_polarized: Enable spin polarization (auto-enabled for Fe, Co, Ni, Mn, Cr)

    Returns:
        Dictionary with total_energy_eV, fermi_energy_eV, forces, convergence status
    
    Examples:
        qe_run_scf(structure="Si")           # All auto
        qe_run_scf(structure="Fe")           # Auto spin-polarized
        qe_run_scf(structure="Cu", conv_thr=1e-8)  # High accuracy
    """
    return run_scf(
        structure=structure,
        ecutwfc=ecutwfc,
        ecutrho=None,
        kpoints=_parse_kpoints(kpoints),
        smearing=None,
        degauss=degauss,
        spin_polarized=spin_polarized,
        conv_thr=conv_thr,
        mixing_beta=mixing_beta,
        prefix=None,
    )


@mcp.tool()
def qe_run_relax(
    structure: str,
    kpoints: str = "auto",
    ecutwfc: float | None = None,
    nstep: int | None = None,
    forc_conv_thr: float | None = None,
    spin_polarized: bool | None = None,
) -> dict:
    """
    Optimize atomic positions (fixed cell relaxation).

    Relaxes atomic positions to minimize forces while keeping the unit cell fixed.
    
    ALL PARAMETERS EXCEPT 'structure' ARE OPTIONAL.

    Args:
        structure: Atomic structure - formula ("Si", "H2O"), file path, or CIF/POSCAR string
        kpoints: K-point grid. Options: "auto" (default), "gamma", "8,8,8"
        ecutwfc: Plane-wave cutoff in Ry (auto-detected if not set)
        nstep: Maximum relaxation steps (default: 100). Increase for complex structures.
        forc_conv_thr: Force convergence threshold in Ry/Bohr (default: 1e-3). Use 1e-4 for high accuracy.
        spin_polarized: Enable spin polarization (auto-enabled for Fe, Co, Ni, Mn, Cr)

    Returns:
        Dictionary with relaxed energy, forces, convergence status
    
    Examples:
        qe_run_relax(structure="H2O")  # Relax water molecule
        qe_run_relax(structure="Si", forc_conv_thr=1e-4)  # Tight convergence
        qe_run_relax(structure="complex_molecule", nstep=200)  # More steps
    """
    return run_relax(
        structure=structure,
        ecutwfc=ecutwfc,
        ecutrho=None,
        kpoints=_parse_kpoints(kpoints),
        smearing=None,
        degauss=None,
        spin_polarized=spin_polarized,
        conv_thr=None,
        forc_conv_thr=forc_conv_thr,
        nstep=nstep,
        mixing_beta=None,
        prefix=None,
    )


@mcp.tool()
def qe_run_vc_relax(
    structure: str,
    kpoints: str = "auto",
    ecutwfc: float | None = None,
    nstep: int | None = None,
    forc_conv_thr: float | None = None,
    press_conv_thr: float | None = None,
    spin_polarized: bool | None = None,
) -> dict:
    """
    Variable-cell relaxation (optimize positions AND cell).

    Optimizes atomic positions and unit cell parameters simultaneously.
    Useful for finding equilibrium lattice constants.
    
    ALL PARAMETERS EXCEPT 'structure' ARE OPTIONAL.

    Args:
        structure: Atomic structure - formula ("Cu", "Au"), file path, or CIF/POSCAR string
        kpoints: K-point grid. Options: "auto" (default), "gamma", "8,8,8"
        ecutwfc: Plane-wave cutoff in Ry (auto-detected if not set)
        nstep: Maximum relaxation steps (default: 100). Increase for complex structures.
        forc_conv_thr: Force convergence threshold in Ry/Bohr (default: 1e-3).
        press_conv_thr: Pressure convergence threshold in kbar (default: 0.5).
        spin_polarized: Enable spin polarization (auto-enabled for Fe, Co, Ni, Mn, Cr)

    Returns:
        Dictionary with relaxed structure, energy, stress, final lattice constants
    
    Examples:
        qe_run_vc_relax(structure="Au")  # Find gold's equilibrium lattice constant
        qe_run_vc_relax(structure="Si", press_conv_thr=0.1)  # Tight pressure convergence
    """
    return run_vc_relax(
        structure=structure,
        ecutwfc=ecutwfc,
        ecutrho=None,
        kpoints=_parse_kpoints(kpoints),
        smearing=None,
        degauss=None,
        spin_polarized=spin_polarized,
        conv_thr=None,
        forc_conv_thr=forc_conv_thr,
        press_conv_thr=press_conv_thr,
        cell_dofree=None,
        nstep=nstep,
        mixing_beta=None,
        prefix=None,
    )


# =============================================================================
# Workflow Tools
# =============================================================================


@mcp.tool()
def qe_workflow_bandstructure(
    structure: str,
    kpoints: str = "auto",
    ecutwfc: float | None = None,
    nbnd: int | None = None,
    npoints_band: int | None = None,
    spin_polarized: bool | None = None,
) -> dict:
    """
    Complete band structure calculation workflow.

    Performs: SCF -> NSCF along k-path -> bands.x
    Automatically determines high-symmetry k-path based on crystal symmetry.
    
    Use this to answer: "Is X a metal or semiconductor?" or "What is the band gap?"

    Args:
        structure: Atomic structure - formula ("Si", "GaAs", "Fe"), file path, or CIF/POSCAR
        kpoints: K-point grid for SCF. Options: "auto" (default), "gamma", "8,8,8"
        ecutwfc: Plane-wave cutoff in Ry (auto-detected if not set)
        nbnd: Number of bands to calculate. Default is 8 per atom. Increase for more 
              conduction bands (e.g., optical properties) or decrease for faster calculation.
        npoints_band: Number of k-points along the band path (default: 100). Use 200+ for 
                      publication-quality smooth bands.
        spin_polarized: Enable spin polarization (auto-enabled for Fe, Co, Ni, Mn, Cr)

    Returns:
        Dictionary with band_gap_eV, is_metal, vbm_eV, cbm_eV, bands_file
    
    Examples:
        qe_workflow_bandstructure(structure="Si")   # Default (100 k-points, 16 bands)
        qe_workflow_bandstructure(structure="Si", nbnd=20, npoints_band=200)  # Smooth, more bands
        qe_workflow_bandstructure(structure="GaAs", nbnd=30)  # Many bands for optics
    """
    return workflow_bandstructure(
        structure=structure,
        ecutwfc=ecutwfc,
        ecutrho=None,
        kpoints_scf=_parse_kpoints(kpoints),
        npoints_band=npoints_band,
        nbnd=nbnd,
        relax_first=None,
        spin_polarized=spin_polarized,
        prefix=None,
    )


@mcp.tool()
def qe_workflow_dos(
    structure: str,
    kpoints: str = "auto",
    ecutwfc: float | None = None,
    emin: float | None = None,
    emax: float | None = None,
    deltae: float | None = None,
    spin_polarized: bool | None = None,
) -> dict:
    """
    Complete density of states (DOS) workflow.

    Performs: SCF -> NSCF (dense k-grid) -> dos.x
    Use for analyzing electronic structure and d-band centers.

    Args:
        structure: Atomic structure - formula ("Cu", "TiO2"), file path, or CIF/POSCAR
        kpoints: K-point grid for SCF. Options: "auto" (default), "gamma", "8,8,8"
        ecutwfc: Plane-wave cutoff in Ry (auto-detected if not set)
        emin: Minimum energy for DOS in eV relative to Fermi (default: -20)
        emax: Maximum energy for DOS in eV relative to Fermi (default: 20)
        deltae: Energy step for DOS in eV (default: 0.01). Smaller = smoother.
        spin_polarized: Enable spin polarization (auto-enabled for Fe, Co, Ni, Mn, Cr)

    Returns:
        Dictionary with dos_file path, fermi_energy_eV, energy_points
    
    Examples:
        qe_workflow_dos(structure="Cu")   # DOS of copper
        qe_workflow_dos(structure="Fe", emin=-10, emax=5)  # Focus on d-band
        qe_workflow_dos(structure="Si", deltae=0.005)  # Very smooth DOS
    """
    return workflow_dos(
        structure=structure,
        ecutwfc=ecutwfc,
        ecutrho=None,
        kpoints_scf=_parse_kpoints(kpoints),
        kpoints_nscf=None,
        emin=emin,
        emax=emax,
        deltae=deltae,
        spin_polarized=spin_polarized,
        prefix=None,
    )


@mcp.tool()
def qe_workflow_relax_and_scf(
    structure: str,
    kpoints: str = "auto",
    variable_cell: bool = False,
    spin_polarized: bool | None = None,
) -> dict:
    """
    Relax structure then compute accurate total energy.

    Performs relaxation followed by high-accuracy SCF for final energy.

    Args:
        structure: Atomic structure - formula ("H2O"), file path, or CIF/POSCAR
        kpoints: K-point grid. Options: "auto" (default), "gamma", "8,8,8"
        variable_cell: If True, also optimize the unit cell (default: False)
        spin_polarized: Enable spin polarization (auto-enabled for Fe, Co, Ni, Mn, Cr)

    Returns:
        Dictionary with relaxation info and final SCF energy
    
    Examples:
        qe_workflow_relax_and_scf(structure="H2O")  # Optimize water
        qe_workflow_relax_and_scf(structure="Cu", variable_cell=True)  # Full optimization
    """
    return workflow_relax_and_scf(
        structure=structure,
        ecutwfc=None,
        ecutrho=None,
        kpoints=_parse_kpoints(kpoints),
        variable_cell=variable_cell,
        spin_polarized=spin_polarized,
        prefix=None,
    )


# =============================================================================
# Utility Tools
# =============================================================================


@mcp.tool()
def qe_load_structure(structure: str) -> dict:
    """
    Load and inspect an atomic structure.

    Supports many input formats:
    - File paths: .cif, .vasp, .poscar, .xyz, .extxyz, .pdb, .xsf
    - Formulas: "Si", "Cu", "GaAs", "NaCl"
    - 2D materials: "graphene", "hBN", "MoS2", "WS2", "phosphorene"
    - Perovskites: "SrTiO3", "BaTiO3", "LaMnO3"
    - Materials Project IDs: "mp-149" (requires MP_API_KEY)
    - Inline XYZ: "xyz:C 0 0 0; C 1.42 0 0|lattice:2.46,0,0,0,4.26,0,0,0,15"
    - Structure data as string (CIF, POSCAR, XYZ content)

    Args:
        structure: Structure specification (see formats above)

    Returns:
        Dictionary with formula, n_atoms, cell, positions, volume
    
    Examples:
        qe_load_structure("graphene")     # Built-in 2D graphene
        qe_load_structure("mp-149")       # Silicon from Materials Project
        qe_load_structure("/path/to/struct.cif")
    """
    return load_structure_tool(structure)


@mcp.tool()
def qe_search_materials_project(
    query: str,
    num_results: int = 10,
) -> dict:
    """
    Search Materials Project database for structures.
    
    Requires MP_API_KEY environment variable.
    Get your API key at: https://materialsproject.org/api
    
    Args:
        query: Search query. Examples:
            - Formula: "Si", "Fe2O3", "LiFePO4"
            - Elements: "Fe-O" (materials with Fe AND O)
            - Chemical system: "Li-Fe-P-O" (all materials in that space)
        num_results: Maximum number of results (default: 10)
    
    Returns:
        Dictionary with:
        - results: List of materials with mp_id, formula, band_gap, etc.
        - hint: How to load a structure using the mp_id
    
    Examples:
        qe_search_materials_project("GaN")        # Find GaN structures
        qe_search_materials_project("Li-Fe-O")    # Lithium iron oxides
        qe_search_materials_project("perovskite") # Search by name
    """
    return search_materials_project(query, num_results=num_results)


@mcp.tool()
def qe_get_mp_structure(mp_id: str) -> dict:
    """
    Get structure from Materials Project by material ID.
    
    Requires MP_API_KEY environment variable.
    
    Args:
        mp_id: Materials Project ID (e.g., "mp-149" for silicon)
    
    Returns:
        Dictionary with structure information (cell, positions, formula)
    
    Examples:
        qe_get_mp_structure("mp-149")     # Silicon
        qe_get_mp_structure("mp-19017")   # Fe2O3
        qe_get_mp_structure("mp-13")      # Fe (BCC)
    """
    return get_mp_structure(mp_id)


@mcp.tool()
def qe_get_kpath(structure: str, npoints: int = 100) -> dict:
    """
    Get high-symmetry k-path for band structure.

    Automatically determines path based on crystal symmetry.

    Args:
        structure: Atomic structure
        npoints: Number of k-points along path

    Returns:
        Dictionary with kpoints, special_points labels, path string
    """
    return get_kpath_tool(structure, npoints)


@mcp.tool()
def qe_suggest_kpoints(
    structure: str,
    density: str = "medium",
    kspacing: float | None = None,
) -> dict:
    """
    Suggest k-point grid for a structure based on cell size.
    
    Uses odd numbers (3, 5, 7, 9, 11, ...) for gamma-centered grids.
    Automatically scales: smaller cells get denser k-grids.

    Args:
        structure: Atomic structure
        density: Preset density level:
            - "low": Quick tests (~25/cell_length)
            - "medium": Production quality (~40/cell_length)
            - "high": High accuracy (~60/cell_length)
        kspacing: Optional explicit spacing in 1/Angstrom (overrides density)

    Returns:
        Dictionary with suggested kpoints grid and cell info
    """
    return suggest_kpoints(structure, density=density, kspacing=kspacing)


@mcp.tool()
def qe_list_pseudopotentials() -> dict:
    """
    List available SG15 ONCV pseudopotentials.

    Returns:
        Dictionary with elements list and recommended cutoffs
    """
    return list_pseudopotentials()


@mcp.tool()
def qe_validate_structure(structure: str) -> dict:
    """
    Validate structure and check for issues.

    Checks pseudopotential availability, atom distances, cell size.

    Args:
        structure: Structure to validate

    Returns:
        Dictionary with validation results, warnings, recommendations
    """
    return validate_structure(structure)


@mcp.tool()
def qe_status() -> dict:
    """
    Get QE MCP server status.

    Returns:
        Dictionary with runner status, pseudopotentials, configuration
    """
    return get_system_status()


# =============================================================================
# Data Access Tools - For Plotting
# =============================================================================


@mcp.tool()
def qe_read_bands(output_dir: str) -> dict:
    """
    Read band structure data from a calculation directory.
    
    Reads the .gnu file (bands.dat.gnu) and returns data ready for plotting.
    Use this to get the raw band structure data after running qe_workflow_bandstructure.

    Args:
        output_dir: Path to the calculation output directory

    Returns:
        Dictionary with:
            - k_distances: List of k-point distances along path
            - energies: List of lists, one per band
            - n_bands: Number of bands
            - n_kpoints: Number of k-points
    
    Example:
        bands = qe_read_bands("/path/to/bands_calculation")
        # Then plot with matplotlib:
        # for band in bands["energies"]:
        #     plt.plot(bands["k_distances"], band)
    """
    return read_bands_gnu(output_dir)


@mcp.tool()
def qe_read_dos(output_dir: str) -> dict:
    """
    Read DOS data from a calculation directory.
    
    Reads the .dat file (prefix.dos or prefix.dos.dat) and returns data for plotting.
    Use this to get the raw DOS data after running qe_workflow_dos.

    Args:
        output_dir: Path to the calculation output directory

    Returns:
        Dictionary with:
            - energies: List of energy values (eV)
            - dos: Density of states values
            - integrated_dos: Integrated DOS values
            - n_points: Number of energy points
    
    Example:
        dos = qe_read_dos("/path/to/dos_calculation")
        # Then plot with matplotlib:
        # plt.plot(dos["energies"], dos["dos"])
    """
    return read_dos_dat(output_dir)


@mcp.tool()
def qe_read_pdos(pdos_file: str) -> dict:
    """
    Read PDOS (projected DOS) data from a specific file.
    
    Reads a PDOS file (e.g., prefix.pdos_atm#1(Fe)_wfc#1(d)) for orbital-resolved plotting.

    Args:
        pdos_file: Path to the specific PDOS file

    Returns:
        Dictionary with:
            - energies: List of energy values (eV)
            - ldos: Local DOS values
            - pdos: Projected DOS per orbital
            - orbitals: List of orbital names
    
    Example:
        pdos = qe_read_pdos("/path/to/prefix.pdos_atm#1(Fe)_wfc#1(d)")
        # Plot d-band:
        # plt.plot(pdos["energies"], pdos["pdos"]["dz2"])
    """
    return read_pdos_dat(pdos_file)


@mcp.tool()
def qe_list_files(output_dir: str) -> dict:
    """
    List available output files in a calculation directory.
    
    Use this to find what files are available for reading/plotting.

    Args:
        output_dir: Path to the calculation output directory

    Returns:
        Dictionary with:
            - bands_files: List of .gnu band structure files
            - dos_files: List of DOS .dat files
            - pdos_files: List of PDOS files
            - output_files: List of .out log files
    """
    return list_calculation_files(output_dir)


# =============================================================================
# Resources - Documentation
# =============================================================================


@mcp.resource("qe://docs/pw")
def resource_pw_docs() -> str:
    """Quantum ESPRESSO pw.x documentation."""
    return get_resource("qe://docs/pw")["text"]


@mcp.resource("qe://docs/pp")
def resource_pp_docs() -> str:
    """Quantum ESPRESSO pp.x documentation."""
    return get_resource("qe://docs/pp")["text"]


@mcp.resource("qe://docs/bands")
def resource_bands_docs() -> str:
    """Quantum ESPRESSO bands.x documentation."""
    return get_resource("qe://docs/bands")["text"]


@mcp.resource("qe://docs/dos")
def resource_dos_docs() -> str:
    """Quantum ESPRESSO dos.x documentation."""
    return get_resource("qe://docs/dos")["text"]


@mcp.resource("qe://docs/projwfc")
def resource_projwfc_docs() -> str:
    """Quantum ESPRESSO projwfc.x documentation."""
    return get_resource("qe://docs/projwfc")["text"]


@mcp.resource("qe://docs/ase")
def resource_ase_docs() -> str:
    """ASE (Atomic Simulation Environment) documentation."""
    return get_resource("qe://docs/ase")["text"]


@mcp.resource("qe://docs/pseudopotentials")
def resource_pseudo_docs() -> str:
    """SG15 ONCV pseudopotential documentation."""
    return get_resource("qe://docs/pseudopotentials")["text"]


@mcp.resource("qe://docs/workflows")
def resource_workflow_docs() -> str:
    """QE-MCP workflow guides."""
    return get_resource("qe://docs/workflows")["text"]


@mcp.resource("qe://llm/decision-guide")
def resource_llm_decision_guide() -> str:
    """LLM decision guide for interpreting user requests."""
    from qe_mcp.resources.llm_context import LLM_DECISION_GUIDE
    return LLM_DECISION_GUIDE


@mcp.resource("qe://llm/examples")
def resource_llm_examples() -> str:
    """Example calculations with expected outputs."""
    from qe_mcp.resources.llm_context import CALCULATION_EXAMPLES
    return CALCULATION_EXAMPLES


@mcp.resource("qe://llm/materials")
def resource_materials_database() -> str:
    """Common materials reference database."""
    from qe_mcp.resources.llm_context import MATERIAL_DATABASE
    return MATERIAL_DATABASE


@mcp.resource("qe://llm/plotting")
def resource_plotting_guide() -> str:
    """Plotting guide with matplotlib code examples for band structures, DOS, and PDOS."""
    from qe_mcp.resources.plotting import PLOTTING_GUIDE
    return PLOTTING_GUIDE


# =============================================================================
# Prompts - Pre-built Templates
# =============================================================================


@mcp.prompt()
def band_structure(material: str, accuracy: str = "medium") -> str:
    """
    Calculate electronic band structure for a material.
    
    Args:
        material: Chemical formula (e.g., 'Si', 'GaAs', 'Fe2O3')
        accuracy: 'low', 'medium', or 'high'
    """
    result = get_prompt("band_structure", {"material": material, "accuracy": accuracy})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def dos_calculation(material: str, spin_polarized: bool = False) -> str:
    """
    Calculate density of states for a material.
    
    Args:
        material: Chemical formula (e.g., 'Cu', 'Fe', 'TiO2')
        spin_polarized: Enable spin polarization for magnetic materials
    """
    result = get_prompt("dos_calculation", {"material": material, "spin_polarized": spin_polarized})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def geometry_optimization(structure: str, optimize_cell: bool = False) -> str:
    """
    Optimize atomic positions and optionally cell parameters.
    
    Args:
        structure: Structure file or formula
        optimize_cell: Whether to optimize unit cell
    """
    result = get_prompt("geometry_optimization", {"structure": structure, "optimize_cell": optimize_cell})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def convergence_test(material: str, parameter: str = "both") -> str:
    """
    Test convergence of calculation parameters.
    
    Args:
        material: Material to test (e.g., 'Si', 'Cu')
        parameter: 'ecutwfc', 'kpoints', or 'both'
    """
    result = get_prompt("convergence_test", {"material": material, "parameter": parameter})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def surface_calculation(material: str, surface: str, layers: int = 6) -> str:
    """
    Calculate surface energy and properties.
    
    Args:
        material: Bulk material (e.g., 'Cu', 'Pt')
        surface: Miller indices (e.g., '111', '100')
        layers: Number of atomic layers
    """
    result = get_prompt("surface_calculation", {"material": material, "surface": surface, "layers": layers})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def magnetic_calculation(material: str, configuration: str = "ferromagnetic") -> str:
    """
    Calculate magnetic properties.
    
    Args:
        material: Magnetic material (e.g., 'Fe', 'Ni')
        configuration: 'ferromagnetic', 'antiferromagnetic', or 'both'
    """
    result = get_prompt("magnetic_calculation", {"material": material, "configuration": configuration})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def troubleshoot(problem: str, material: str = "") -> str:
    """
    Help diagnose and fix DFT calculation issues.
    
    Args:
        problem: Description of the problem
        material: Material being calculated (optional)
    """
    result = get_prompt("troubleshoot", {"problem": problem, "material": material})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def compare_structures(structures: str) -> str:
    """
    Compare energies and properties of different structures.
    
    Args:
        structures: Comma-separated list of structures
    """
    result = get_prompt("compare_structures", {"structures": structures})
    return result["messages"][0]["content"]["text"]


# =============================================================================
# Entry Point
# =============================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
