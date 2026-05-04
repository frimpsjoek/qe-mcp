"""
Workflow tools for QE MCP server.

Multi-step calculation workflows that combine multiple QE calculations.
"""

import uuid
import shutil
from pathlib import Path
from typing import Any

from qe_mcp.config import QEConfig
from qe_mcp.core.structures import load_structure, get_kpath, atoms_to_dict
from qe_mcp.core.pseudopotentials import SG15Library
from qe_mcp.core.runner import get_runner
from qe_mcp.core.parser import QEOutputParser
from qe_mcp.core.input_generator import (
    generate_pw_input,
    generate_bands_input,
    generate_dos_input,
)




# Elements that typically require spin-polarized calculations
MAGNETIC_ELEMENTS = {'Fe', 'Co', 'Ni', 'Mn', 'Cr', 'V', 'Gd', 'Eu', 'Tb', 'Dy', 'Ho', 'Er'}


def _detect_magnetic(atoms) -> bool:
    """Detect if structure contains magnetic elements."""
    return bool(set(atoms.get_chemical_symbols()) & MAGNETIC_ELEMENTS)


def _apply_workflow_defaults(
    atoms,
    spin_polarized: bool | None,
    npoints_band: int | None = None,
    relax_first: bool | None = None,
    deltae: float | None = None,
    variable_cell: bool | None = None,
) -> dict:
    """Apply smart defaults for workflow parameters."""
    is_magnetic = _detect_magnetic(atoms)
    
    return {
        'spin_polarized': spin_polarized if spin_polarized is not None else is_magnetic,
        'npoints_band': npoints_band if npoints_band is not None else 100,
        'relax_first': relax_first if relax_first is not None else False,
        'deltae': deltae if deltae is not None else 0.01,
        'variable_cell': variable_cell if variable_cell is not None else False,
    }




# Elements that typically require spin-polarized calculations
MAGNETIC_ELEMENTS = {'Fe', 'Co', 'Ni', 'Mn', 'Cr', 'V', 'Gd', 'Eu', 'Tb', 'Dy', 'Ho', 'Er'}


def _detect_magnetic(atoms) -> bool:
    """Detect if structure contains magnetic elements."""
    return bool(set(atoms.get_chemical_symbols()) & MAGNETIC_ELEMENTS)


def _apply_workflow_defaults(
    atoms,
    spin_polarized: bool | None,
    npoints_band: int | None = None,
    relax_first: bool | None = None,
    deltae: float | None = None,
    variable_cell: bool | None = None,
) -> dict:
    """Apply smart defaults for workflow parameters."""
    is_magnetic = _detect_magnetic(atoms)
    
    return {
        'spin_polarized': spin_polarized if spin_polarized is not None else is_magnetic,
        'npoints_band': npoints_band if npoints_band is not None else 100,
        'relax_first': relax_first if relax_first is not None else False,
        'deltae': deltae if deltae is not None else 0.01,
        'variable_cell': variable_cell if variable_cell is not None else False,
    }


def workflow_bandstructure(
    structure: str,
    ecutwfc: float | None = None,
    ecutrho: float | None = None,
    kpoints_scf: list[int] | None = None,
    npoints_band: int | None = None,
    nbnd: int | None = None,
    relax_first: bool | None = None,
    spin_polarized: bool | None = None,
    prefix: str | None = None,
) -> dict[str, Any]:
    """
    Complete band structure workflow.

    Performs the following steps:
    1. (Optional) Relax structure
    2. SCF calculation for charge density
    3. NSCF calculation along high-symmetry k-path
    4. bands.x to extract band structure

    Args:
        structure: Atomic structure (file, string, or formula like "Si")
        ecutwfc: Plane-wave cutoff in Ry (auto if None)
        ecutrho: Density cutoff in Ry (auto if None)
        kpoints_scf: K-point grid for SCF [n1, n2, n3] (auto if None)
        npoints_band: Number of k-points along band path
        nbnd: Number of bands to calculate (default: 8 per atom, good for most cases)
        relax_first: If True, relax structure before band calculation
        spin_polarized: Enable spin polarization
        prefix: Workflow name

    Returns:
        Dictionary containing:
        - success: Overall workflow success
        - band_gap_eV: Band gap in eV (None if metal)
        - is_metal: Whether the system is metallic
        - vbm_eV: Valence band maximum
        - cbm_eV: Conduction band minimum
        - fermi_energy_eV: Fermi energy
        - total_energy_eV: Total energy from SCF
        - bands_file: Path to bands.dat
        - high_symmetry_points: Dict of special k-point labels
        - output_dir: Workflow directory
    """
    config = QEConfig.from_environment()
    workflow_id = prefix or f"bands_{uuid.uuid4().hex[:8]}"
    workflow_dir = config.workdir / workflow_id
    workflow_dir.mkdir(parents=True, exist_ok=True)

    # Load structure
    atoms = load_structure(structure)
    elements = list(set(atoms.get_chemical_symbols()))

    # Apply smart defaults
    defaults = _apply_workflow_defaults(
        atoms=atoms,
        spin_polarized=spin_polarized,
        npoints_band=npoints_band,
        relax_first=relax_first,
    )
    spin_polarized = defaults['spin_polarized']
    npoints_band = defaults['npoints_band']
    relax_first = defaults['relax_first']

    # Setup pseudopotentials
    pseudo_dir = workflow_dir / "pseudo"
    pseudo_dir.mkdir(exist_ok=True)
    pseudo_lib = SG15Library(config.pseudo_dir)

    for el in elements:
        pseudo_info = pseudo_lib.get(el)
        shutil.copy(pseudo_info.path, pseudo_dir / pseudo_info.filename)

    # Auto cutoffs
    if ecutwfc is None or ecutrho is None:
        rec_wfc, rec_rho = pseudo_lib.get_recommended_cutoffs(elements)
        ecutwfc = ecutwfc or rec_wfc
        ecutrho = ecutrho or rec_rho

    runner = get_runner(config)
    results = {"workflow_id": workflow_id, "output_dir": str(workflow_dir)}

    # Step 1: Optional relaxation
    if relax_first:
        relax_input = generate_pw_input(
            atoms=atoms,
            pseudo_lib=pseudo_lib,
            calculation="relax",
            prefix=workflow_id,
            ecutwfc=ecutwfc,
            ecutrho=ecutrho,
            kpoints=kpoints_scf,
            spin_polarized=spin_polarized,
        )
        relax_file = workflow_dir / "relax.in"
        relax_file.write_text(relax_input)

        relax_result = runner.run(
            executable="pw.x",
            input_file=relax_file,
            output_file=workflow_dir / "relax.out",
            work_dir=workflow_dir,
            nprocs=config.nprocs,
        )

        if not relax_result.success:
            return {
                "success": False,
                "step_failed": "relax",
                "error": relax_result.error_message,
                **results,
            }

        # TODO: Parse relaxed structure from output
        results["relaxation"] = "completed"

    # Step 2: SCF calculation
    scf_input = generate_pw_input(
        atoms=atoms,
        pseudo_lib=pseudo_lib,
        calculation="scf",
        prefix=workflow_id,
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints_scf,
        spin_polarized=spin_polarized,
    )
    scf_file = workflow_dir / "scf.in"
    scf_file.write_text(scf_input)

    scf_result = runner.run(
        executable="pw.x",
        input_file=scf_file,
        output_file=workflow_dir / "scf.out",
        work_dir=workflow_dir,
        nprocs=config.nprocs,
    )

    if not scf_result.success:
        return {
            "success": False,
            "step_failed": "scf",
            "error": scf_result.error_message,
            **results,
        }

    scf_parsed = QEOutputParser.parse_scf(scf_result.stdout)
    results["total_energy_eV"] = scf_parsed.total_energy_ev
    results["fermi_energy_eV"] = scf_parsed.fermi_energy_ev

    # Step 3: NSCF bands calculation
    # Get k-path
    kpts, special_points = get_kpath(atoms, npoints=npoints_band)

    nscf_input = generate_pw_input(
        atoms=atoms,
        pseudo_lib=pseudo_lib,
        calculation="bands",
        prefix=workflow_id,
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints_crystal=kpts.tolist(),
        spin_polarized=spin_polarized,
        nbnd=nbnd if nbnd is not None else len(atoms) * 8,  # LLM can override, default 8 per atom
        nosym=True,
    )
    nscf_file = workflow_dir / "nscf.in"
    nscf_file.write_text(nscf_input)

    nscf_result = runner.run(
        executable="pw.x",
        input_file=nscf_file,
        output_file=workflow_dir / "nscf.out",
        work_dir=workflow_dir,
        nprocs=config.nprocs,
    )

    if not nscf_result.success:
        return {
            "success": False,
            "step_failed": "nscf",
            "error": nscf_result.error_message,
            **results,
        }

    # Step 4: bands.x
    bands_input = generate_bands_input(
        prefix=workflow_id,
        outdir="./tmp",
        filband="bands.dat",
    )
    bands_file = workflow_dir / "bands.in"
    bands_file.write_text(bands_input)

    bands_result = runner.run(
        executable="bands.x",
        input_file=bands_file,
        output_file=workflow_dir / "bands.out",
        work_dir=workflow_dir,
        nprocs=1,
    )

    if not bands_result.success:
        return {
            "success": False,
            "step_failed": "bands",
            "error": bands_result.error_message,
            **results,
        }

    # Parse bands
    bands_dat = workflow_dir / "bands.dat"
    if bands_dat.exists():
        bands_parsed = QEOutputParser.parse_bands_dat(
            bands_dat, scf_parsed.fermi_energy_ev
        )
        
        # Check if gap is direct (VBM and CBM at same k-point)
        is_direct = False
        vbm_kpt_idx = None
        cbm_kpt_idx = None
        if not bands_parsed.is_metal and bands_parsed.eigenvalues:
            fermi = scf_parsed.fermi_energy_ev or 0
            vbm_val, cbm_val = float('-inf'), float('inf')
            for kpt_idx, eigs in enumerate(bands_parsed.eigenvalues):
                for e in eigs:
                    if e <= fermi and e > vbm_val:
                        vbm_val, vbm_kpt_idx = e, kpt_idx
                    if e > fermi and e < cbm_val:
                        cbm_val, cbm_kpt_idx = e, kpt_idx
            is_direct = (vbm_kpt_idx == cbm_kpt_idx)
        
        # Convert special_points to JSON-serializable format
        special_points_json = {k: v.tolist() if hasattr(v, 'tolist') else list(v) 
                               for k, v in special_points.items()}
        
        results.update({
            "success": True,
            "band_gap_eV": bands_parsed.band_gap_ev,
            "is_metal": bands_parsed.is_metal,
            "is_direct_gap": is_direct,
            "vbm_eV": bands_parsed.vbm_ev,
            "cbm_eV": bands_parsed.cbm_ev,
            "n_bands": bands_parsed.n_bands,
            "n_kpoints": bands_parsed.n_kpoints,
            "high_symmetry_points": special_points_json,
            # Include eigenvalue data for plotting!
            "eigenvalues_eV": bands_parsed.eigenvalues,  # [kpt_idx][band_idx] 
            "kpoints": bands_parsed.kpoints,  # [[kx, ky, kz], ...]
            # File paths (for reference)
            "bands_file": str(bands_dat),
            "output_dir": str(workflow_dir),
        })
    else:
        # FAIL properly, don't fake success
        return {
            "success": False,
            "step_failed": "parse_bands",
            "error": "bands.dat not found - bands.x may have failed",
            **results,
        }

    return results


def workflow_dos(
    structure: str,
    ecutwfc: float | None = None,
    ecutrho: float | None = None,
    kpoints_scf: list[int] | None = None,
    kpoints_nscf: list[int] | None = None,
    emin: float | None = None,
    emax: float | None = None,
    deltae: float | None = None,
    spin_polarized: bool | None = None,
    prefix: str | None = None,
) -> dict[str, Any]:
    """
    Complete DOS workflow.

    Performs:
    1. SCF calculation
    2. NSCF calculation with dense k-grid
    3. dos.x to compute DOS

    Args:
        structure: Atomic structure
        ecutwfc: Plane-wave cutoff in Ry
        ecutrho: Density cutoff in Ry
        kpoints_scf: K-grid for SCF
        kpoints_nscf: Denser k-grid for NSCF (default: 2x SCF grid)
        emin: Min energy for DOS (eV, relative to Fermi)
        emax: Max energy for DOS (eV)
        deltae: Energy step (eV)
        spin_polarized: Enable spin polarization
        prefix: Workflow name

    Returns:
        Dictionary with DOS results and file paths
    """
    config = QEConfig.from_environment()
    workflow_id = prefix or f"dos_{uuid.uuid4().hex[:8]}"
    workflow_dir = config.workdir / workflow_id
    workflow_dir.mkdir(parents=True, exist_ok=True)

    atoms = load_structure(structure)
    elements = list(set(atoms.get_chemical_symbols()))

    pseudo_dir = workflow_dir / "pseudo"
    pseudo_dir.mkdir(exist_ok=True)
    pseudo_lib = SG15Library(config.pseudo_dir)

    for el in elements:
        pseudo_info = pseudo_lib.get(el)
        shutil.copy(pseudo_info.path, pseudo_dir / pseudo_info.filename)

    if ecutwfc is None or ecutrho is None:
        rec_wfc, rec_rho = pseudo_lib.get_recommended_cutoffs(elements)
        ecutwfc = ecutwfc or rec_wfc
        ecutrho = ecutrho or rec_rho

    # Default to denser k-grid for NSCF
    if kpoints_nscf is None and kpoints_scf is not None:
        kpoints_nscf = [k * 2 for k in kpoints_scf]

    runner = get_runner(config)
    results = {"workflow_id": workflow_id, "output_dir": str(workflow_dir)}

    # Step 1: SCF
    scf_input = generate_pw_input(
        atoms=atoms,
        pseudo_lib=pseudo_lib,
        calculation="scf",
        prefix=workflow_id,
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints_scf,
        spin_polarized=spin_polarized,
    )
    scf_file = workflow_dir / "scf.in"
    scf_file.write_text(scf_input)

    scf_result = runner.run(
        executable="pw.x",
        input_file=scf_file,
        output_file=workflow_dir / "scf.out",
        work_dir=workflow_dir,
        nprocs=config.nprocs,
    )

    if not scf_result.success:
        return {
            "success": False,
            "step_failed": "scf",
            "error": scf_result.error_message,
            **results,
        }

    scf_parsed = QEOutputParser.parse_scf(scf_result.stdout)
    results["total_energy_eV"] = scf_parsed.total_energy_ev
    results["fermi_energy_eV"] = scf_parsed.fermi_energy_ev

    # Step 2: NSCF with dense k-grid
    nscf_input = generate_pw_input(
        atoms=atoms,
        pseudo_lib=pseudo_lib,
        calculation="nscf",
        prefix=workflow_id,
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints_nscf,
        spin_polarized=spin_polarized,
        occupations="tetrahedra",  # Better for DOS
    )
    nscf_file = workflow_dir / "nscf.in"
    nscf_file.write_text(nscf_input)

    nscf_result = runner.run(
        executable="pw.x",
        input_file=nscf_file,
        output_file=workflow_dir / "nscf.out",
        work_dir=workflow_dir,
        nprocs=config.nprocs,
    )

    if not nscf_result.success:
        return {
            "success": False,
            "step_failed": "nscf",
            "error": nscf_result.error_message,
            **results,
        }

    # Step 3: dos.x
    dos_input = generate_dos_input(
        prefix=workflow_id,
        outdir="./tmp",
        fildos="dos.dat",
        emin=emin,
        emax=emax,
        deltae=deltae,
    )
    dos_file = workflow_dir / "dos.in"
    dos_file.write_text(dos_input)

    dos_result = runner.run(
        executable="dos.x",
        input_file=dos_file,
        output_file=workflow_dir / "dos.out",
        work_dir=workflow_dir,
        nprocs=1,
    )

    if not dos_result.success:
        return {
            "success": False,
            "step_failed": "dos",
            "error": dos_result.error_message,
            **results,
        }

    dos_dat = workflow_dir / "dos.dat"
    if dos_dat.exists():
        dos_parsed = QEOutputParser.parse_dos(dos_dat)
        results.update({
            "success": True,
            # Include actual DOS data for plotting!
            "energies_eV": dos_parsed.energies,  # Energy values
            "dos": dos_parsed.dos,               # DOS values
            "integrated_dos": dos_parsed.integrated_dos,
            "dos_fermi_eV": dos_parsed.fermi_energy_ev,
            "energy_range_eV": [
                min(dos_parsed.energies) if dos_parsed.energies else None,
                max(dos_parsed.energies) if dos_parsed.energies else None,
            ],
            "n_points": len(dos_parsed.energies),
            # File paths (for reference)
            "dos_file": str(dos_dat),
            "output_dir": str(workflow_dir),
        })
    else:
        # FAIL properly
        return {
            "success": False,
            "step_failed": "parse_dos",
            "error": "dos.dat not found - dos.x may have failed",
            **results,
        }

    return results


def workflow_relax_and_scf(
    structure: str,
    ecutwfc: float | None = None,
    ecutrho: float | None = None,
    kpoints: list[int] | None = None,
    variable_cell: bool | None = None,
    spin_polarized: bool | None = None,
    prefix: str | None = None,
) -> dict[str, Any]:
    """
    Relax structure then perform accurate SCF.

    Useful for getting accurate energies after relaxation.

    Args:
        structure: Atomic structure
        ecutwfc: Plane-wave cutoff in Ry
        ecutrho: Density cutoff in Ry
        kpoints: K-point grid
        variable_cell: If True, use vc-relax (optimize cell too)
        spin_polarized: Enable spin polarization
        prefix: Workflow name

    Returns:
        Dictionary with relaxation and final SCF results
    """
    config = QEConfig.from_environment()
    workflow_id = prefix or f"relax_scf_{uuid.uuid4().hex[:8]}"
    workflow_dir = config.workdir / workflow_id
    workflow_dir.mkdir(parents=True, exist_ok=True)

    atoms = load_structure(structure)
    elements = list(set(atoms.get_chemical_symbols()))

    pseudo_dir = workflow_dir / "pseudo"
    pseudo_dir.mkdir(exist_ok=True)
    pseudo_lib = SG15Library(config.pseudo_dir)

    for el in elements:
        pseudo_info = pseudo_lib.get(el)
        shutil.copy(pseudo_info.path, pseudo_dir / pseudo_info.filename)

    if ecutwfc is None or ecutrho is None:
        rec_wfc, rec_rho = pseudo_lib.get_recommended_cutoffs(elements)
        ecutwfc = ecutwfc or rec_wfc
        ecutrho = ecutrho or rec_rho

    runner = get_runner(config)
    results = {"workflow_id": workflow_id, "output_dir": str(workflow_dir)}

    # Step 1: Relaxation
    calc_type = "vc-relax" if variable_cell else "relax"
    relax_input = generate_pw_input(
        atoms=atoms,
        pseudo_lib=pseudo_lib,
        calculation=calc_type,
        prefix=workflow_id,
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints,
        spin_polarized=spin_polarized,
    )
    relax_file = workflow_dir / "relax.in"
    relax_file.write_text(relax_input)

    relax_result = runner.run(
        executable="pw.x",
        input_file=relax_file,
        output_file=workflow_dir / "relax.out",
        work_dir=workflow_dir,
        nprocs=config.nprocs,
    )

    relax_parsed = QEOutputParser.parse_scf(relax_result.stdout)
    results["relaxation"] = {
        "success": relax_result.success,
        "converged": "End of BFGS" in relax_result.stdout,
        "energy_eV": relax_parsed.total_energy_ev,
    }

    if not relax_result.success:
        return {
            "success": False,
            "step_failed": "relax",
            "error": relax_result.error_message,
            **results,
        }

    # Step 2: Final SCF
    # Note: We should ideally read relaxed structure, but for now
    # we restart from the saved charge density
    scf_input = generate_pw_input(
        atoms=atoms,  # TODO: Use relaxed structure
        pseudo_lib=pseudo_lib,
        calculation="scf",
        prefix=workflow_id,
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints,
        spin_polarized=spin_polarized,
        conv_thr=1.0e-8,  # Tighter convergence for final energy
    )
    scf_file = workflow_dir / "scf.in"
    scf_file.write_text(scf_input)

    scf_result = runner.run(
        executable="pw.x",
        input_file=scf_file,
        output_file=workflow_dir / "scf.out",
        work_dir=workflow_dir,
        nprocs=config.nprocs,
    )

    scf_parsed = QEOutputParser.parse_scf(scf_result.stdout)

    results.update({
        "success": scf_result.success and scf_parsed.converged,
        "total_energy_eV": scf_parsed.total_energy_ev,
        "total_energy_Ry": scf_parsed.total_energy_ry,
        "fermi_energy_eV": scf_parsed.fermi_energy_ev,
        "forces_eV_per_angstrom": scf_parsed.forces,
    })

    return results
