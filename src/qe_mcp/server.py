"""
Quantum ESPRESSO MCP Server.

A Model Context Protocol server for running DFT calculations
using Quantum ESPRESSO with SG15 ONCV pseudopotentials.
"""

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env file
# Ensure we get the absolute path
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

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
from qe_mcp.tools.job_status import get_job_status
from qe_mcp.resources import list_resources, get_resource
from qe_mcp.prompts import list_prompts, get_prompt
from qe_mcp.skills import list_skills, get_skill

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
    runner: str | None = None,
) -> dict:
    """
    Run an SCF calculation and return energy, Fermi level, forces, and status.
    Only structure is required; kpoints accepts "auto", "gamma", "8,8,8", or "12".
    runner may be "docker", "local", "globus", or "polaris".
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
        runner=runner,
    )


@mcp.tool()
def qe_run_relax(
    structure: str,
    kpoints: str = "auto",
    ecutwfc: float | None = None,
    nstep: int | None = None,
    forc_conv_thr: float | None = None,
    spin_polarized: bool | None = None,
    runner: str | None = None,
) -> dict:
    """
    Relax atomic positions with a fixed cell.
    Only structure is required; optional cutoff, force threshold, steps, spin,
    kpoints, and runner override the automatic defaults.
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
        runner=runner,
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
    runner: str | None = None,
) -> dict:
    """
    Relax atomic positions and cell parameters.
    Use for equilibrium lattice constants or bulk cell optimization. Only
    structure is required; optional thresholds and runner override defaults.
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
        runner=runner,
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
    runner: str | None = None,
) -> dict:
    """
    Run SCF -> NSCF along a symmetry k-path -> bands.x.
    Returns band-gap metadata and output paths or an async job_id. For plots,
    use qe_read_bands and generate Python matplotlib only, never JavaScript.
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
        runner=runner,
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
    runner: str | None = None,
) -> dict:
    """
    Run SCF -> dense NSCF -> dos.x.
    Returns DOS output paths or an async job_id. For plots, use qe_read_dos
    and generate Python matplotlib only, never JavaScript.
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
        runner=runner,
    )


@mcp.tool()
def qe_workflow_relax_and_scf(
    structure: str,
    kpoints: str = "auto",
    variable_cell: bool = False,
    spin_polarized: bool | None = None,
    runner: str | None = None,
) -> dict:
    """
    Relax a structure, then run a final SCF for accurate total energy.
    Set variable_cell=true to optimize lattice vectors as well as atoms.
    """
    return workflow_relax_and_scf(
        structure=structure,
        ecutwfc=None,
        ecutrho=None,
        kpoints=_parse_kpoints(kpoints),
        variable_cell=variable_cell,
        spin_polarized=spin_polarized,
        prefix=None,
        runner=runner,
    )


# =============================================================================
# Utility Tools
# =============================================================================


@mcp.tool()
def qe_load_structure(structure: str) -> dict:
    """
    Load a formula, file path, Materials Project ID, inline XYZ, or structure
    text and return formula, atoms, cell, positions, volume, and PBC metadata.
    """
    return load_structure_tool(structure)


@mcp.tool()
def qe_search_materials_project(
    query: str,
    num_results: int = 10,
) -> dict:
    """
    Search Materials Project by formula or chemical system.
    Requires MP_API_KEY. Use qe_get_mp_structure or qe_load_structure with
    the returned material_id to load a result.
    """
    return search_materials_project(query, num_results=num_results)


@mcp.tool()
def qe_get_mp_structure(mp_id: str) -> dict:
    """
    Load a Materials Project structure by ID, e.g. "mp-149".
    Requires MP_API_KEY and returns the same structure metadata as qe_load_structure.
    """
    return get_mp_structure(mp_id)


@mcp.tool()
def qe_get_kpath(structure: str, npoints: int = 100) -> dict:
    """
    Return a symmetry-derived band-structure k-path for a structure.
    Includes k-points, special point labels, and a path label string.
    """
    return get_kpath_tool(structure, npoints)


@mcp.tool()
def qe_suggest_kpoints(
    structure: str,
    density: str = "medium",
    kspacing: float | None = None,
) -> dict:
    """
    Suggest an automatic k-point grid from cell size.
    density is "low", "medium", or "high"; kspacing overrides density.
    """
    return suggest_kpoints(structure, density=density, kspacing=kspacing)


@mcp.tool()
def qe_list_pseudopotentials() -> dict:
    """
    List available SG15 ONCV pseudopotentials and cutoff hints.
    """
    return list_pseudopotentials()


@mcp.tool()
def qe_validate_structure(structure: str) -> dict:
    """
    Validate loadability, pseudopotentials, atom distances, and cell volume.
    Returns errors, warnings, and recommended cutoffs/k-points.
    """
    return validate_structure(structure)


@mcp.tool()
def qe_status() -> dict:
    """
    Return runner availability, pseudopotential status, and active config.
    """
    return get_system_status()


@mcp.tool()
def qe_get_job_status(job_id: str) -> dict:
    """
    Check an async job_id returned by Polaris/Globus submissions.
    May advance multi-step workflows. If pending, do not poll rapidly; use
    qe-watch or check again later.
    """
    return get_job_status(job_id)


# =============================================================================
# Data Access Tools - For Plotting
# =============================================================================


@mcp.tool()
def qe_read_bands(output_dir: str) -> dict:
    """
    Read bands.dat.gnu into k_distances and per-band energies.
    Plot with Python matplotlib only unless explicitly requested otherwise.
    Never default to JavaScript, Chart.js, Plotly, HTML canvas, or browser plotting.
    """
    return read_bands_gnu(output_dir)


@mcp.tool()
def qe_read_dos(output_dir: str) -> dict:
    """
    Read total DOS data into energies, dos, and integrated_dos arrays.
    Plot with Python matplotlib only unless explicitly requested otherwise.
    Never default to JavaScript, Chart.js, Plotly, HTML canvas, or browser plotting.
    """
    return read_dos_dat(output_dir)


@mcp.tool()
def qe_read_pdos(pdos_file: str) -> dict:
    """
    Read one projected DOS file into energies, local DOS, orbitals, and PDOS.
    Plot with Python matplotlib only unless explicitly requested otherwise.
    Never default to JavaScript, Chart.js, Plotly, HTML canvas, or browser plotting.
    """
    return read_pdos_dat(pdos_file)


@mcp.tool()
def qe_list_files(output_dir: str) -> dict:
    """
    List bands, DOS, PDOS, and .out files in a calculation directory.
    Use before qe_read_bands, qe_read_dos, or qe_read_pdos.
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
    return get_resource("qe://llm/decision-guide")["text"]


@mcp.resource("qe://llm/examples")
def resource_llm_examples() -> str:
    """Example calculations with expected outputs."""
    return get_resource("qe://llm/examples")["text"]


@mcp.resource("qe://llm/materials")
def resource_materials_database() -> str:
    """Common materials reference database."""
    return get_resource("qe://llm/materials")["text"]


@mcp.resource("qe://llm/plotting")
def resource_plotting_guide() -> str:
    """Plotting guide with matplotlib code examples for band structures, DOS, and PDOS."""
    return get_resource("qe://llm/plotting")["text"]


@mcp.resource("qe://llm/pre-calculation-guide")
def resource_pre_calculation_guide() -> str:
    """Pre-calculation triage guide — when to ask, when to default, what to confirm."""
    return get_resource("qe://llm/pre-calculation-guide")["text"]


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
# Skills - Action-Oriented Workflows
# =============================================================================


@mcp.prompt()
def skill_band_structure(material: str, accuracy: str = "medium") -> str:
    """
    Action-oriented band structure skill: validates structure, previews k-path,
    runs the full workflow with async handoff, and returns interpreted results
    plus publication-quality plotting code.

    Args:
        material: Chemical formula or structure (e.g., 'Si', 'GaAs', 'Fe2O3')
        accuracy: 'low', 'medium', or 'high'
    """
    result = get_skill("band_structure", {"material": material, "accuracy": accuracy})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_dos(material: str, spin_polarized: bool = False) -> str:
    """
    Action-oriented DOS + PDOS skill: auto-detects magnetic elements, runs the
    full workflow with async handoff, and returns orbital/exchange-splitting
    interpretation plus plotting code.

    Args:
        material: Chemical formula or structure (e.g., 'Cu', 'Fe', 'TiO2')
        spin_polarized: Enable spin polarization (auto-detected for magnetic elements)
    """
    result = get_skill("dos", {"material": material, "spin_polarized": spin_polarized})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_relax(structure: str, optimize_cell: bool = False) -> str:
    """
    Smart geometry optimization skill: auto-selects relax vs vc-relax based on
    system type (bulk crystal / slab / molecule), handles async jobs, and reports full
    structural change summary.

    Args:
        structure: Structure file, formula, or inline coordinates
        optimize_cell: Whether to also optimize the unit cell
    """
    result = get_skill("relax", {"structure": structure, "optimize_cell": optimize_cell})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_scf(material: str) -> str:
    """
    Quick single-point SCF skill: runs with smart defaults, handles async jobs, and
    reports energy, Fermi level, and magnetization.

    Args:
        material: Chemical formula or structure (e.g., 'Si', 'Cu', 'Fe2O3')
    """
    result = get_skill("scf", {"material": material})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_magnetic(material: str, configuration: str = "ferromagnetic") -> str:
    """
    Magnetic properties skill: calculates FM and/or AFM states, exchange energy,
    and spin-polarized DOS to determine the magnetic ground state.

    Args:
        material: Magnetic material (e.g., 'Fe', 'Ni', 'MnO')
        configuration: 'ferromagnetic', 'antiferromagnetic', or 'both'
    """
    result = get_skill("magnetic", {"material": material, "configuration": configuration})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_convergence(material: str, parameter: str = "both") -> str:
    """
    Convergence testing skill: runs systematic ecutwfc and k-point sweeps,
    builds convergence tables, and recommends optimal parameters.

    Args:
        material: Material to test (e.g., 'Si', 'Cu')
        parameter: 'ecutwfc', 'kpoints', or 'both'
    """
    result = get_skill("convergence", {"material": material, "parameter": parameter})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_compare(structures: str) -> str:
    """
    Structure comparison skill: runs consistent SCF calculations on multiple
    structures and ranks them by thermodynamic stability (energy/atom).

    Args:
        structures: Comma-separated list of structures/formulas to compare
    """
    result = get_skill("compare", {"structures": structures})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_plot(job_id: str) -> str:
    """
    Plotting skill: discovers available output data (bands, DOS, PDOS) for a
    completed job and generates a complete, ready-to-run publication-quality
    matplotlib script (no placeholders).

    Args:
        job_id: Job ID or working directory path from a completed calculation
    """
    result = get_skill("plot", {"job_id": job_id})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_report(job_id: str) -> str:
    """
    Analysis report skill: reads all output files for a completed job and
    generates a structured report covering parameters, results, physical
    interpretation, DFT caveats, and next steps.

    Args:
        job_id: Job ID of the completed calculation
    """
    result = get_skill("report", {"job_id": job_id})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_status(job_ids: str = "") -> str:
    """
    Status dashboard skill: reports server/runner health and the status of
    one or more jobs with next-step suggestions for failed runs.

    Args:
        job_ids: Optional comma-separated job IDs to check (blank = server health only)
    """
    result = get_skill("status", {"job_ids": job_ids})
    return result["messages"][0]["content"]["text"]


@mcp.prompt()
def skill_troubleshoot(problem: str, material: str = "") -> str:
    """
    Troubleshooting skill: classifies the failure (SCF convergence, geometry
    stall, memory, bands mismatch, pseudopotential), reads output files if a
    job ID is identifiable, and proposes a corrected tool call.

    Args:
        problem: Description of the problem (e.g., 'SCF not converging for NiO')
        material: Material being calculated (optional)
    """
    result = get_skill("troubleshoot", {"problem": problem, "material": material})
    return result["messages"][0]["content"]["text"]


# =============================================================================
# Entry Point
# =============================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
