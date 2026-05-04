"""
Core DFT calculation tools for QE MCP server.

These tools run pw.x calculations (SCF, relax, vc-relax).
All parameters are optional - smart defaults are applied based on material type.
"""

import os
import uuid
import shutil
from pathlib import Path
from typing import Any

from qe_mcp.config import QEConfig
from qe_mcp.core.structures import load_structure, atoms_to_dict
from qe_mcp.core.pseudopotentials import SG15Library
from qe_mcp.core.runner import get_runner
from qe_mcp.core.parser import QEOutputParser
from qe_mcp.core.input_generator import generate_pw_input
from qe_mcp.core.job_registry import JobRegistry


# Elements that typically require spin-polarized calculations
MAGNETIC_ELEMENTS = {'Fe', 'Co', 'Ni', 'Mn', 'Cr', 'V', 'Gd', 'Eu', 'Tb', 'Dy', 'Ho', 'Er'}


def _detect_magnetic(atoms) -> bool:
    """Detect if structure contains magnetic elements."""
    return bool(set(atoms.get_chemical_symbols()) & MAGNETIC_ELEMENTS)


def _apply_smart_defaults(
    atoms,
    smearing: str | None,
    degauss: float | None,
    spin_polarized: bool | None,
    conv_thr: float | None,
    mixing_beta: float | None,
    forc_conv_thr: float | None = None,
    nstep: int | None = None,
    press_conv_thr: float | None = None,
    cell_dofree: str | None = None,
) -> dict:
    """
    Apply smart defaults based on material type.
    
    Auto-detects:
    - spin_polarized: True for Fe, Co, Ni, Mn, Cr, V, etc.
    - smearing: 'cold' (Marzari-Vanderbilt) - good for metals and semiconductors
    - degauss: 0.02 Ry (~0.27 eV) - good general value
    """
    # Detect magnetic elements
    is_magnetic = _detect_magnetic(atoms)
    
    # Smart defaults
    defaults = {
        'smearing': smearing if smearing is not None else 'cold',
        'degauss': degauss if degauss is not None else 0.02,
        'spin_polarized': spin_polarized if spin_polarized is not None else is_magnetic,
        'conv_thr': conv_thr if conv_thr is not None else 1.0e-6,
        'mixing_beta': mixing_beta if mixing_beta is not None else 0.7,
        'forc_conv_thr': forc_conv_thr if forc_conv_thr is not None else 1.0e-3,
        'nstep': nstep if nstep is not None else 100,
        'press_conv_thr': press_conv_thr if press_conv_thr is not None else 0.5,
        'cell_dofree': cell_dofree if cell_dofree is not None else 'all',
    }
    
    return defaults


def _setup_calculation(
    structure: str,
    calculation: str,
    ecutwfc: float | None,
    ecutrho: float | None,
    kpoints: list[int] | None,
    smearing: str | None,
    degauss: float | None,
    spin_polarized: bool | None,
    conv_thr: float | None,
    mixing_beta: float | None,
    prefix: str | None,
    **kwargs,
) -> tuple[str, Path, Path, Path, QEConfig, dict]:
    """Common setup for calculations. Returns (calc_id, calc_dir, input_file, output_file, config, defaults)."""
    config = QEConfig.from_environment()
    config.workdir.mkdir(parents=True, exist_ok=True)

    # Load structure
    atoms = load_structure(structure)
    elements = list(set(atoms.get_chemical_symbols()))

    # Apply smart defaults based on material
    defaults = _apply_smart_defaults(
        atoms=atoms,
        smearing=smearing,
        degauss=degauss,
        spin_polarized=spin_polarized,
        conv_thr=conv_thr,
        mixing_beta=mixing_beta,
        forc_conv_thr=kwargs.get('forc_conv_thr'),
        nstep=kwargs.get('nstep'),
        press_conv_thr=kwargs.get('press_conv_thr'),
        cell_dofree=kwargs.get('cell_dofree'),
    )

    # Setup calculation directory
    calc_id = prefix or f"{calculation}_{uuid.uuid4().hex[:8]}"
    calc_dir = config.workdir / calc_id
    calc_dir.mkdir(parents=True, exist_ok=True)

    # Copy pseudopotentials
    pseudo_dir = calc_dir / "pseudo"
    pseudo_dir.mkdir(exist_ok=True)
    pseudo_lib = SG15Library(config.pseudo_dir)

    for el in elements:
        pseudo_info = pseudo_lib.get(el)
        shutil.copy(pseudo_info.path, pseudo_dir / pseudo_info.filename)

    # Generate input file
    input_content = generate_pw_input(
        atoms=atoms,
        pseudo_lib=pseudo_lib,
        calculation=calculation,
        prefix=calc_id,
        outdir="./tmp",
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints,
        smearing=defaults['smearing'],
        degauss=defaults['degauss'],
        spin_polarized=defaults['spin_polarized'],
        conv_thr=defaults['conv_thr'],
        mixing_beta=defaults['mixing_beta'],
        forc_conv_thr=defaults['forc_conv_thr'],
        nstep=defaults['nstep'],
        press_conv_thr=defaults.get('press_conv_thr'),
        cell_dofree=defaults.get('cell_dofree'),
    )

    input_file = calc_dir / f"{calc_id}.in"
    input_file.write_text(input_content)

    output_file = calc_dir / f"{calc_id}.out"

    return calc_id, calc_dir, input_file, output_file, config, defaults


def run_scf(
    structure: str,
    ecutwfc: float | None = None,
    ecutrho: float | None = None,
    kpoints: list[int] | None = None,
    smearing: str | None = None,
    degauss: float | None = None,
    spin_polarized: bool | None = None,
    conv_thr: float | None = None,
    mixing_beta: float | None = None,
    prefix: str | None = None,
    runner: str | None = None,
) -> dict[str, Any]:
    """
    Run a self-consistent field (SCF) DFT calculation.

    All parameters except 'structure' are optional and auto-detected.
    """
    calc_id, calc_dir, input_file, output_file, config, defaults = _setup_calculation(
        structure=structure,
        calculation="scf",
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints,
        smearing=smearing,
        degauss=degauss,
        spin_polarized=spin_polarized,
        conv_thr=conv_thr,
        mixing_beta=mixing_beta,
        prefix=prefix,
    )

    # Run calculation
    runner_instance = get_runner(config, runner_type=runner)
    result = runner_instance.run(
        executable="pw.x",
        input_file=input_file,
        output_file=output_file,
        work_dir=calc_dir,
        nprocs=config.nprocs,
    )

    if result.in_progress:
        runner_used = runner or os.environ.get("QE_RUNNER", "globus")
        JobRegistry(config.workdir).register(
            job_id=calc_id, task_id=result.task_id, runner=runner_used,
            calc_type="scf", work_dir=str(calc_dir), structure=structure,
        )
        return {
            "status": "submitted",
            "job_id": calc_id,
            "task_id": result.task_id,
            "output_dir": str(calc_dir),
            "message": f"SCF submitted to Polaris. Poll with qe_get_status(job_id='{calc_id}').",
        }

    # Parse output
    scf_result = QEOutputParser.parse_scf(result.stdout)

    return {
        "success": result.success and scf_result.converged,
        "converged": scf_result.converged,
        "total_energy_eV": scf_result.total_energy_ev,
        "total_energy_Ry": scf_result.total_energy_ry,
        "fermi_energy_eV": scf_result.fermi_energy_ev,
        "n_iterations": scf_result.n_iterations,
        "forces_eV_per_angstrom": scf_result.forces,
        "stress_kbar": scf_result.stress_kbar,
        "total_magnetization": scf_result.total_magnetization,
        "walltime_seconds": result.walltime_seconds,
        "output_dir": str(calc_dir),
        "output_file": str(output_file),
        "parameters_used": {
            "spin_polarized": defaults['spin_polarized'],
            "smearing": defaults['smearing'],
            "degauss": defaults['degauss'],
        },
        "errors": [result.error_message] if result.error_message else None,
    }


def run_relax(
    structure: str,
    ecutwfc: float | None = None,
    ecutrho: float | None = None,
    kpoints: list[int] | None = None,
    smearing: str | None = None,
    degauss: float | None = None,
    spin_polarized: bool | None = None,
    conv_thr: float | None = None,
    forc_conv_thr: float | None = None,
    nstep: int | None = None,
    mixing_beta: float | None = None,
    prefix: str | None = None,
    runner: str | None = None,
) -> dict[str, Any]:
    """
    Run atomic position relaxation (fixed cell).

    All parameters except 'structure' are optional and auto-detected.
    """
    calc_id, calc_dir, input_file, output_file, config, defaults = _setup_calculation(
        structure=structure,
        calculation="relax",
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints,
        smearing=smearing,
        degauss=degauss,
        spin_polarized=spin_polarized,
        conv_thr=conv_thr,
        mixing_beta=mixing_beta,
        prefix=prefix,
        forc_conv_thr=forc_conv_thr,
        nstep=nstep,
    )

    runner_instance = get_runner(config, runner_type=runner)
    result = runner_instance.run(
        executable="pw.x",
        input_file=input_file,
        output_file=output_file,
        work_dir=calc_dir,
        nprocs=config.nprocs,
    )

    if result.in_progress:
        runner_used = runner or os.environ.get("QE_RUNNER", "globus")
        JobRegistry(config.workdir).register(
            job_id=calc_id, task_id=result.task_id, runner=runner_used,
            calc_type="relax", work_dir=str(calc_dir), structure=structure,
        )
        return {
            "status": "submitted",
            "job_id": calc_id,
            "task_id": result.task_id,
            "output_dir": str(calc_dir),
            "message": f"Relax submitted to Polaris. Poll with qe_get_status(job_id='{calc_id}').",
        }

    scf_result = QEOutputParser.parse_scf(result.stdout)

    # Check if relaxation converged
    relax_converged = "Final energy" in result.stdout or (
        "End of BFGS Geometry Optimization" in result.stdout
    )

    return {
        "success": result.success and relax_converged,
        "converged": scf_result.converged,
        "relaxation_converged": relax_converged,
        "total_energy_eV": scf_result.total_energy_ev,
        "total_energy_Ry": scf_result.total_energy_ry,
        "fermi_energy_eV": scf_result.fermi_energy_ev,
        "forces_eV_per_angstrom": scf_result.forces,
        "total_force_Ry_Bohr": scf_result.total_force_ry_bohr,
        "walltime_seconds": result.walltime_seconds,
        "output_dir": str(calc_dir),
        "output_file": str(output_file),
        "parameters_used": {
            "spin_polarized": defaults['spin_polarized'],
            "smearing": defaults['smearing'],
        },
        "errors": [result.error_message] if result.error_message else None,
    }


def run_vc_relax(
    structure: str,
    ecutwfc: float | None = None,
    ecutrho: float | None = None,
    kpoints: list[int] | None = None,
    smearing: str | None = None,
    degauss: float | None = None,
    spin_polarized: bool | None = None,
    conv_thr: float | None = None,
    forc_conv_thr: float | None = None,
    press_conv_thr: float | None = None,
    cell_dofree: str | None = None,
    nstep: int | None = None,
    mixing_beta: float | None = None,
    prefix: str | None = None,
    runner: str | None = None,
) -> dict[str, Any]:
    """
    Run variable-cell relaxation (optimize both positions and cell).

    All parameters except 'structure' are optional and auto-detected.
    """
    calc_id, calc_dir, input_file, output_file, config, defaults = _setup_calculation(
        structure=structure,
        calculation="vc-relax",
        ecutwfc=ecutwfc,
        ecutrho=ecutrho,
        kpoints=kpoints,
        smearing=smearing,
        degauss=degauss,
        spin_polarized=spin_polarized,
        conv_thr=conv_thr,
        mixing_beta=mixing_beta,
        prefix=prefix,
        forc_conv_thr=forc_conv_thr,
        press_conv_thr=press_conv_thr,
        cell_dofree=cell_dofree,
        nstep=nstep,
    )

    runner_instance = get_runner(config, runner_type=runner)
    result = runner_instance.run(
        executable="pw.x",
        input_file=input_file,
        output_file=output_file,
        work_dir=calc_dir,
        nprocs=config.nprocs,
    )

    if result.in_progress:
        runner_used = runner or os.environ.get("QE_RUNNER", "globus")
        JobRegistry(config.workdir).register(
            job_id=calc_id, task_id=result.task_id, runner=runner_used,
            calc_type="vc-relax", work_dir=str(calc_dir), structure=structure,
        )
        return {
            "status": "submitted",
            "job_id": calc_id,
            "task_id": result.task_id,
            "output_dir": str(calc_dir),
            "message": f"VC-Relax submitted to Polaris. Poll with qe_get_status(job_id='{calc_id}').",
        }

    scf_result = QEOutputParser.parse_scf(result.stdout)

    relax_converged = "End of BFGS Geometry Optimization" in result.stdout

    return {
        "success": result.success and relax_converged,
        "converged": scf_result.converged,
        "relaxation_converged": relax_converged,
        "total_energy_eV": scf_result.total_energy_ev,
        "total_energy_Ry": scf_result.total_energy_ry,
        "fermi_energy_eV": scf_result.fermi_energy_ev,
        "forces_eV_per_angstrom": scf_result.forces,
        "stress_kbar": scf_result.stress_kbar,
        "walltime_seconds": result.walltime_seconds,
        "output_dir": str(calc_dir),
        "output_file": str(output_file),
        "parameters_used": {
            "spin_polarized": defaults['spin_polarized'],
            "smearing": defaults['smearing'],
            "cell_dofree": defaults['cell_dofree'],
        },
        "errors": [result.error_message] if result.error_message else None,
    }
