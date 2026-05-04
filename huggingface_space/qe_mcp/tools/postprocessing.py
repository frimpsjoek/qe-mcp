"""
Post-processing tools for QE MCP server.

Tools for bands.x, dos.x, projwfc.x, pp.x calculations.
"""

import uuid
from pathlib import Path
from typing import Any

from qe_mcp.config import QEConfig
from qe_mcp.core.runner import get_runner
from qe_mcp.core.parser import QEOutputParser
from qe_mcp.core.input_generator import (
    generate_bands_input,
    generate_dos_input,
    generate_projwfc_input,
)


def run_bands(
    scf_dir: str,
    prefix: str | None = None,
) -> dict[str, Any]:
    """
    Run bands.x to extract band structure data.

    Must be run after an NSCF bands calculation.

    Args:
        scf_dir: Directory containing completed NSCF bands calculation
        prefix: Calculation prefix (auto-detected if None)

    Returns:
        Dictionary with band structure data
    """
    config = QEConfig.from_environment()
    calc_dir = Path(scf_dir)

    # Auto-detect prefix from directory
    if prefix is None:
        # Look for .in files
        in_files = list(calc_dir.glob("*.in"))
        if in_files:
            prefix = in_files[0].stem
        else:
            prefix = "calc"

    # Generate bands.x input
    bands_input = generate_bands_input(
        prefix=prefix,
        outdir="./tmp",
        filband="bands.dat",
    )

    input_file = calc_dir / "bands.in"
    input_file.write_text(bands_input)
    output_file = calc_dir / "bands.out"

    # Run bands.x
    runner = get_runner(config)
    result = runner.run(
        executable="bands.x",
        input_file=input_file,
        output_file=output_file,
        work_dir=calc_dir,
        nprocs=1,  # bands.x is usually serial
    )

    if not result.success:
        return {
            "success": False,
            "error": result.error_message or "bands.x failed",
            "output_dir": str(calc_dir),
        }

    # Parse bands data
    bands_file = calc_dir / "bands.dat"
    if bands_file.exists():
        # Try to get Fermi energy from previous SCF
        fermi_energy = None
        scf_out_files = list(calc_dir.glob("*.out"))
        for out_file in scf_out_files:
            if out_file.name != "bands.out":
                scf_result = QEOutputParser.parse_scf(out_file.read_text())
                if scf_result.fermi_energy_ev:
                    fermi_energy = scf_result.fermi_energy_ev
                    break

        bands_result = QEOutputParser.parse_bands_dat(bands_file, fermi_energy)

        return {
            "success": True,
            "n_bands": bands_result.n_bands,
            "n_kpoints": bands_result.n_kpoints,
            "fermi_energy_eV": bands_result.fermi_energy_ev,
            "band_gap_eV": bands_result.band_gap_ev,
            "is_metal": bands_result.is_metal,
            "vbm_eV": bands_result.vbm_ev,
            "cbm_eV": bands_result.cbm_ev,
            "bands_file": str(bands_file),
            "output_dir": str(calc_dir),
        }
    else:
        return {
            "success": False,
            "error": "bands.dat not found",
            "output_dir": str(calc_dir),
        }


def run_dos(
    scf_dir: str,
    prefix: str | None = None,
    emin: float | None = None,
    emax: float | None = None,
    deltae: float = 0.01,
) -> dict[str, Any]:
    """
    Run dos.x to calculate density of states.

    Must be run after an NSCF calculation with dense k-points.

    Args:
        scf_dir: Directory containing completed NSCF calculation
        prefix: Calculation prefix
        emin: Minimum energy (eV), relative to Fermi
        emax: Maximum energy (eV), relative to Fermi
        deltae: Energy grid spacing (eV)

    Returns:
        Dictionary with DOS data
    """
    config = QEConfig.from_environment()
    calc_dir = Path(scf_dir)

    if prefix is None:
        in_files = list(calc_dir.glob("*.in"))
        if in_files:
            prefix = in_files[0].stem
        else:
            prefix = "calc"

    dos_input = generate_dos_input(
        prefix=prefix,
        outdir="./tmp",
        fildos="dos.dat",
        emin=emin,
        emax=emax,
        deltae=deltae,
    )

    input_file = calc_dir / "dos.in"
    input_file.write_text(dos_input)
    output_file = calc_dir / "dos.out"

    runner = get_runner(config)
    result = runner.run(
        executable="dos.x",
        input_file=input_file,
        output_file=output_file,
        work_dir=calc_dir,
        nprocs=1,
    )

    if not result.success:
        return {
            "success": False,
            "error": result.error_message or "dos.x failed",
            "output_dir": str(calc_dir),
        }

    dos_file = calc_dir / "dos.dat"
    if dos_file.exists():
        dos_result = QEOutputParser.parse_dos(dos_file)

        return {
            "success": True,
            "fermi_energy_eV": dos_result.fermi_energy_ev,
            "energy_range_eV": [
                min(dos_result.energies) if dos_result.energies else None,
                max(dos_result.energies) if dos_result.energies else None,
            ],
            "n_points": len(dos_result.energies),
            "dos_file": str(dos_file),
            "output_dir": str(calc_dir),
        }
    else:
        return {
            "success": False,
            "error": "dos.dat not found",
            "output_dir": str(calc_dir),
        }


def run_pdos(
    scf_dir: str,
    prefix: str | None = None,
    emin: float | None = None,
    emax: float | None = None,
    deltae: float = 0.01,
) -> dict[str, Any]:
    """
    Run projwfc.x to calculate projected density of states.

    Decomposes DOS onto atomic orbitals.

    Args:
        scf_dir: Directory containing completed NSCF calculation
        prefix: Calculation prefix
        emin: Minimum energy (eV)
        emax: Maximum energy (eV)
        deltae: Energy grid spacing (eV)

    Returns:
        Dictionary with PDOS file locations
    """
    config = QEConfig.from_environment()
    calc_dir = Path(scf_dir)

    if prefix is None:
        in_files = list(calc_dir.glob("*.in"))
        if in_files:
            prefix = in_files[0].stem
        else:
            prefix = "calc"

    projwfc_input = generate_projwfc_input(
        prefix=prefix,
        outdir="./tmp",
        filpdos="pdos",
        emin=emin,
        emax=emax,
        deltae=deltae,
    )

    input_file = calc_dir / "projwfc.in"
    input_file.write_text(projwfc_input)
    output_file = calc_dir / "projwfc.out"

    runner = get_runner(config)
    result = runner.run(
        executable="projwfc.x",
        input_file=input_file,
        output_file=output_file,
        work_dir=calc_dir,
        nprocs=config.nprocs,
    )

    if not result.success:
        return {
            "success": False,
            "error": result.error_message or "projwfc.x failed",
            "output_dir": str(calc_dir),
        }

    # Find PDOS files
    pdos_files = list(calc_dir.glob("pdos*"))

    return {
        "success": True,
        "pdos_files": [str(f) for f in pdos_files],
        "n_files": len(pdos_files),
        "output_dir": str(calc_dir),
    }
