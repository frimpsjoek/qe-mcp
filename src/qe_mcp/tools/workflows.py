"""
Workflow tools for QE MCP server.

Multi-step calculation workflows that combine multiple QE calculations.
Each workflow supports:
  - Step resumability: skips steps whose output files already exist on disk.
  - Async (Globus) mode: submits the first step and returns a job_id immediately;
    call qe_get_status(job_id) to advance through remaining steps.
"""

import json
import os
import uuid
import shutil
from pathlib import Path
from typing import Any

from qe_mcp.config import QEConfig
from qe_mcp.core.structures import load_structure, get_kpath, atoms_to_dict
from qe_mcp.core.pseudopotentials import SG15Library
from qe_mcp.core.runner import get_runner
from qe_mcp.core.parser import QEOutputParser
from qe_mcp.core.job_registry import JobRegistry
from qe_mcp.core.input_generator import (
    generate_pw_input,
    generate_bands_input,
    generate_dos_input,
)

MAGNETIC_ELEMENTS = {'Fe', 'Co', 'Ni', 'Mn', 'Cr', 'V', 'Gd', 'Eu', 'Tb', 'Dy', 'Ho', 'Er'}


def _detect_magnetic(atoms) -> bool:
    return bool(set(atoms.get_chemical_symbols()) & MAGNETIC_ELEMENTS)


def _apply_workflow_defaults(
    atoms,
    spin_polarized: bool | None,
    npoints_band: int | None = None,
    relax_first: bool | None = None,
    deltae: float | None = None,
    variable_cell: bool | None = None,
) -> dict:
    return {
        'spin_polarized': spin_polarized if spin_polarized is not None else _detect_magnetic(atoms),
        'npoints_band': npoints_band if npoints_band is not None else 100,
        'relax_first': relax_first if relax_first is not None else False,
        'deltae': deltae if deltae is not None else 0.01,
        'variable_cell': variable_cell if variable_cell is not None else False,
    }


# ---------------------------------------------------------------------------
# Step resumability helpers
# ---------------------------------------------------------------------------

def _pw_step_done(work_dir: Path, output_file: str, workflow_id: str) -> bool:
    """Return True if a pw.x step finished successfully and its save dir exists."""
    out = work_dir / output_file
    if not out.exists() or out.stat().st_size == 0:
        return False
    content = out.read_text(errors="replace")
    if "JOB DONE" not in content:
        return False
    # Wavefunction directory must still be present for subsequent steps
    save_dir = work_dir / "tmp" / f"{workflow_id}.save"
    return save_dir.exists()


def _postproc_step_done(work_dir: Path, output_file: str, result_file: str) -> bool:
    """Return True if a post-processing step already produced its result file."""
    out = work_dir / output_file
    res = work_dir / result_file
    return out.exists() and res.exists() and res.stat().st_size > 0


# ---------------------------------------------------------------------------
# Manifest helpers (async workflow state machine)
# ---------------------------------------------------------------------------

def _save_manifest(work_dir: Path, manifest: dict) -> None:
    (work_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str)
    )


def _register_workflow(config: QEConfig, workflow_id: str, task_id: str, runner_used: str,
                       workflow_type: str, work_dir: Path, structure: str) -> None:
    JobRegistry(config.workdir).register(
        job_id=workflow_id,
        task_id=task_id,
        runner=runner_used,
        calc_type=f"workflow_{workflow_type}",
        work_dir=str(work_dir),
        structure=structure,
    )


# ---------------------------------------------------------------------------
# Band structure result parser (shared by sync path and async finalize)
# ---------------------------------------------------------------------------

def _parse_band_results(
    work_dir: Path,
    workflow_id: str,
    fermi_ev: float | None,
    special_points: dict,
) -> dict:
    """Parse bands.dat or bands.dat.gnu and return result dict fields."""
    bands_dat = work_dir / "bands.dat"
    bands_gnu = work_dir / "bands.dat.gnu"

    if bands_dat.exists():
        parsed = QEOutputParser.parse_bands_dat(bands_dat, fermi_ev)
        eigenvalues = parsed.eigenvalues
        n_bands    = parsed.n_bands
        n_kpoints  = parsed.n_kpoints
        band_gap   = parsed.band_gap_ev
        is_metal   = parsed.is_metal
        vbm        = parsed.vbm_ev
        cbm        = parsed.cbm_ev
        kpoints    = parsed.kpoints
        bands_file = str(bands_dat)

    elif bands_gnu.exists():
        eigenvalues = []
        current_band: list[float] = []
        with open(bands_gnu) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    if current_band:
                        eigenvalues.append(current_band)
                        current_band = []
                else:
                    parts = line.split()
                    if len(parts) >= 2:
                        current_band.append(float(parts[1]))
        if current_band:
            eigenvalues.append(current_band)

        if eigenvalues:
            n_bands   = len(eigenvalues)
            n_kpoints = len(eigenvalues[0])
            eigenvalues = [
                [eigenvalues[b][k] for b in range(n_bands)]
                for k in range(n_kpoints)
            ]
        else:
            n_bands = n_kpoints = 0

        ef = fermi_ev or 0.0
        vbm = max((e for kpt in eigenvalues for e in kpt if e <= ef), default=None)
        cbm = min((e for kpt in eigenvalues for e in kpt if e > ef), default=None)
        is_metal  = cbm is None
        band_gap  = (cbm - vbm) if (vbm is not None and cbm is not None) else None
        kpoints   = None
        bands_file = str(bands_gnu)

    else:
        return {
            "success": False,
            "step_failed": "parse_bands",
            "error": "Neither bands.dat nor bands.dat.gnu found",
        }

    # Determine if gap is direct
    is_direct = False
    if not is_metal and eigenvalues:
        ef = fermi_ev or 0.0
        vbm_val, cbm_val = float('-inf'), float('inf')
        vbm_kpt_idx = cbm_kpt_idx = None
        for kpt_idx, eigs in enumerate(eigenvalues):
            for e in eigs:
                if e <= ef and e > vbm_val:
                    vbm_val, vbm_kpt_idx = e, kpt_idx
                if e > ef and e < cbm_val:
                    cbm_val, cbm_kpt_idx = e, kpt_idx
        is_direct = (vbm_kpt_idx == cbm_kpt_idx)

    sp_json = {k: v.tolist() if hasattr(v, 'tolist') else list(v)
               for k, v in special_points.items()}

    return {
        "success": True,
        "band_gap_eV": band_gap,
        "is_metal": is_metal,
        "is_direct_gap": is_direct,
        "vbm_eV": vbm,
        "cbm_eV": cbm,
        "n_bands": n_bands,
        "n_kpoints": n_kpoints,
        "high_symmetry_points": sp_json,
        "eigenvalues_eV": eigenvalues,
        "kpoints": kpoints,
        "bands_file": bands_file,
        "output_dir": str(work_dir),
    }


# ---------------------------------------------------------------------------
# Workflow: band structure
# ---------------------------------------------------------------------------

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
    runner: str | None = None,
) -> dict[str, Any]:
    """
    Complete band structure workflow: SCF → NSCF → bands.x

    Steps are skipped when their output files already exist (resumable).
    With the Globus runner, submits the first pending step and returns
    a job_id; call qe_get_status(job_id) to advance to subsequent steps.
    """
    config = QEConfig.from_environment()
    workflow_id = prefix or f"bands_{uuid.uuid4().hex[:8]}"
    workflow_dir = config.workdir / workflow_id
    workflow_dir.mkdir(parents=True, exist_ok=True)

    atoms = load_structure(structure)
    elements = list(set(atoms.get_chemical_symbols()))

    defaults = _apply_workflow_defaults(
        atoms=atoms, spin_polarized=spin_polarized,
        npoints_band=npoints_band, relax_first=relax_first,
    )
    spin_polarized = defaults['spin_polarized']
    npoints_band   = defaults['npoints_band']

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

    nbnd_actual = nbnd if nbnd is not None else len(atoms) * 8
    runner_instance = get_runner(config, runner_type=runner)
    runner_used = runner or os.environ.get("QE_RUNNER", "globus")
    results: dict = {"workflow_id": workflow_id, "output_dir": str(workflow_dir)}

    # Pre-compute k-path once (needed for NSCF step and manifest)
    kpts, special_points = get_kpath(atoms, npoints=npoints_band)
    kpts_list = kpts.tolist()

    # ---- Step 1: SCF -------------------------------------------------------
    scf_out   = workflow_dir / "scf.out"
    scf_file  = workflow_dir / "scf.in"
    scf_parsed = None

    if _pw_step_done(workflow_dir, "scf.out", workflow_id):
        scf_parsed = QEOutputParser.parse_scf(scf_out.read_text(errors="replace"))
    else:
        scf_input = generate_pw_input(
            atoms=atoms, pseudo_lib=pseudo_lib, calculation="scf",
            prefix=workflow_id, ecutwfc=ecutwfc, ecutrho=ecutrho,
            kpoints=kpoints_scf, spin_polarized=spin_polarized,
        )
        scf_file.write_text(scf_input)

        scf_result = runner_instance.run(
            executable="pw.x", input_file=scf_file,
            output_file=scf_out, work_dir=workflow_dir, nprocs=config.nprocs,
        )

        if scf_result.in_progress:
            manifest = {
                "workflow_type": "bandstructure", "workflow_id": workflow_id,
                "steps": ["scf", "nscf", "bands"], "step_idx": 0,
                "task_id": scf_result.task_id, "output_file": "scf.out",
                "runner": runner_used,
                "params": {
                    "structure": structure, "ecutwfc": ecutwfc, "ecutrho": ecutrho,
                    "kpoints_scf": kpoints_scf, "spin_polarized": spin_polarized,
                    "nbnd": nbnd_actual, "npoints_band": npoints_band,
                    "kpts": kpts_list,
                    "special_points": {k: list(v) for k, v in special_points.items()},
                    "nprocs": config.nprocs,
                },
                "partial": {},
            }
            _save_manifest(workflow_dir, manifest)
            _register_workflow(config, workflow_id, scf_result.task_id,
                               runner_used, "bandstructure", workflow_dir, structure)
            return {
                "status": "submitted", "job_id": workflow_id,
                "current_step": "scf", "output_dir": str(workflow_dir),
                "message": f"SCF submitted. Poll with qe_get_status(job_id='{workflow_id}').",
            }

        if not scf_result.success:
            return {"success": False, "step_failed": "scf",
                    "error": scf_result.error_message, **results}

        scf_parsed = QEOutputParser.parse_scf(scf_result.stdout)

    results["total_energy_eV"]  = scf_parsed.total_energy_ev
    results["fermi_energy_eV"]  = scf_parsed.fermi_energy_ev

    # ---- Step 2: NSCF ------------------------------------------------------
    nscf_out  = workflow_dir / "nscf.out"
    nscf_file = workflow_dir / "nscf.in"

    if not _pw_step_done(workflow_dir, "nscf.out", workflow_id):
        nscf_input = generate_pw_input(
            atoms=atoms, pseudo_lib=pseudo_lib, calculation="bands",
            prefix=workflow_id, ecutwfc=ecutwfc, ecutrho=ecutrho,
            kpoints_crystal=kpts_list, spin_polarized=spin_polarized,
            nbnd=nbnd_actual, nosym=True,
        )
        nscf_file.write_text(nscf_input)

        nscf_result = runner_instance.run(
            executable="pw.x", input_file=nscf_file,
            output_file=nscf_out, work_dir=workflow_dir, nprocs=config.nprocs,
        )

        if nscf_result.in_progress:
            manifest = {
                "workflow_type": "bandstructure", "workflow_id": workflow_id,
                "steps": ["scf", "nscf", "bands"], "step_idx": 1,
                "task_id": nscf_result.task_id, "output_file": "nscf.out",
                "runner": runner_used,
                "params": {
                    "structure": structure, "ecutwfc": ecutwfc, "ecutrho": ecutrho,
                    "kpoints_scf": kpoints_scf, "spin_polarized": spin_polarized,
                    "nbnd": nbnd_actual, "npoints_band": npoints_band,
                    "kpts": kpts_list,
                    "special_points": {k: list(v) for k, v in special_points.items()},
                    "nprocs": config.nprocs,
                },
                "partial": {
                    "total_energy_eV": scf_parsed.total_energy_ev,
                    "fermi_energy_eV": scf_parsed.fermi_energy_ev,
                },
            }
            _save_manifest(workflow_dir, manifest)
            _register_workflow(config, workflow_id, nscf_result.task_id,
                               runner_used, "bandstructure", workflow_dir, structure)
            return {
                "status": "submitted", "job_id": workflow_id,
                "current_step": "nscf", "output_dir": str(workflow_dir),
                "message": f"NSCF submitted (SCF was cached). Poll with qe_get_status(job_id='{workflow_id}').",
                **results,
            }

        if not nscf_result.success:
            return {"success": False, "step_failed": "nscf",
                    "error": nscf_result.error_message, **results}

    # ---- Step 3: bands.x ---------------------------------------------------
    bands_file = workflow_dir / "bands.in"
    bands_out  = workflow_dir / "bands.out"

    if not _postproc_step_done(workflow_dir, "bands.out", "bands.dat") and \
       not (workflow_dir / "bands.dat.gnu").exists():
        bands_input = generate_bands_input(
            prefix=workflow_id, outdir="./tmp", filband="bands.dat",
        )
        bands_file.write_text(bands_input)

        bands_result = runner_instance.run(
            executable="bands.x", input_file=bands_file,
            output_file=bands_out, work_dir=workflow_dir, nprocs=1,
        )

        if bands_result.in_progress:
            manifest = {
                "workflow_type": "bandstructure", "workflow_id": workflow_id,
                "steps": ["scf", "nscf", "bands"], "step_idx": 2,
                "task_id": bands_result.task_id, "output_file": "bands.out",
                "runner": runner_used,
                "params": {
                    "structure": structure, "ecutwfc": ecutwfc, "ecutrho": ecutrho,
                    "kpoints_scf": kpoints_scf, "spin_polarized": spin_polarized,
                    "nbnd": nbnd_actual, "npoints_band": npoints_band,
                    "kpts": kpts_list,
                    "special_points": {k: list(v) for k, v in special_points.items()},
                    "nprocs": config.nprocs,
                },
                "partial": {
                    "total_energy_eV": scf_parsed.total_energy_ev,
                    "fermi_energy_eV": scf_parsed.fermi_energy_ev,
                },
            }
            _save_manifest(workflow_dir, manifest)
            _register_workflow(config, workflow_id, bands_result.task_id,
                               runner_used, "bandstructure", workflow_dir, structure)
            return {
                "status": "submitted", "job_id": workflow_id,
                "current_step": "bands", "output_dir": str(workflow_dir),
                "message": f"bands.x submitted (SCF+NSCF cached). Poll with qe_get_status(job_id='{workflow_id}').",
                **results,
            }

        if not bands_result.success:
            return {"success": False, "step_failed": "bands",
                    "error": bands_result.error_message, **results}

    # ---- Parse final result ------------------------------------------------
    band_results = _parse_band_results(
        workflow_dir, workflow_id, scf_parsed.fermi_energy_ev, special_points,
    )
    results.update(band_results)
    return results


# ---------------------------------------------------------------------------
# Workflow: DOS
# ---------------------------------------------------------------------------

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
    runner: str | None = None,
) -> dict[str, Any]:
    """
    Complete DOS workflow: SCF → NSCF (dense k-grid) → dos.x

    Steps are skipped when their output files already exist (resumable).
    With the Globus runner, submits the first pending step and returns
    a job_id; call qe_get_status(job_id) to advance.
    """
    config = QEConfig.from_environment()
    workflow_id = prefix or f"dos_{uuid.uuid4().hex[:8]}"
    workflow_dir = config.workdir / workflow_id
    workflow_dir.mkdir(parents=True, exist_ok=True)

    atoms = load_structure(structure)
    elements = list(set(atoms.get_chemical_symbols()))

    spin_polarized = spin_polarized if spin_polarized is not None else _detect_magnetic(atoms)
    deltae_actual  = deltae if deltae is not None else 0.01

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

    if kpoints_nscf is None and kpoints_scf is not None:
        kpoints_nscf = [k * 2 for k in kpoints_scf]

    runner_instance = get_runner(config, runner_type=runner)
    runner_used = runner or os.environ.get("QE_RUNNER", "globus")
    results: dict = {"workflow_id": workflow_id, "output_dir": str(workflow_dir)}

    # ---- Step 1: SCF -------------------------------------------------------
    scf_out    = workflow_dir / "scf.out"
    scf_file   = workflow_dir / "scf.in"
    scf_parsed = None

    if _pw_step_done(workflow_dir, "scf.out", workflow_id):
        scf_parsed = QEOutputParser.parse_scf(scf_out.read_text(errors="replace"))
    else:
        scf_input = generate_pw_input(
            atoms=atoms, pseudo_lib=pseudo_lib, calculation="scf",
            prefix=workflow_id, ecutwfc=ecutwfc, ecutrho=ecutrho,
            kpoints=kpoints_scf, spin_polarized=spin_polarized,
        )
        scf_file.write_text(scf_input)

        scf_result = runner_instance.run(
            executable="pw.x", input_file=scf_file,
            output_file=scf_out, work_dir=workflow_dir, nprocs=config.nprocs,
        )

        if scf_result.in_progress:
            manifest = {
                "workflow_type": "dos", "workflow_id": workflow_id,
                "steps": ["scf", "nscf", "dos"], "step_idx": 0,
                "task_id": scf_result.task_id, "output_file": "scf.out",
                "runner": runner_used,
                "params": {
                    "structure": structure, "ecutwfc": ecutwfc, "ecutrho": ecutrho,
                    "kpoints_scf": kpoints_scf, "kpoints_nscf": kpoints_nscf,
                    "spin_polarized": spin_polarized, "emin": emin, "emax": emax,
                    "deltae": deltae_actual, "nprocs": config.nprocs,
                },
                "partial": {},
            }
            _save_manifest(workflow_dir, manifest)
            _register_workflow(config, workflow_id, scf_result.task_id,
                               runner_used, "dos", workflow_dir, structure)
            return {
                "status": "submitted", "job_id": workflow_id,
                "current_step": "scf", "output_dir": str(workflow_dir),
                "message": f"SCF submitted. Poll with qe_get_status(job_id='{workflow_id}').",
            }

        if not scf_result.success:
            return {"success": False, "step_failed": "scf",
                    "error": scf_result.error_message, **results}

        scf_parsed = QEOutputParser.parse_scf(scf_result.stdout)

    results["total_energy_eV"] = scf_parsed.total_energy_ev
    results["fermi_energy_eV"] = scf_parsed.fermi_energy_ev

    # ---- Step 2: NSCF -------------------------------------------------------
    nscf_out  = workflow_dir / "nscf.out"
    nscf_file = workflow_dir / "nscf.in"

    if not _pw_step_done(workflow_dir, "nscf.out", workflow_id):
        nscf_input = generate_pw_input(
            atoms=atoms, pseudo_lib=pseudo_lib, calculation="nscf",
            prefix=workflow_id, ecutwfc=ecutwfc, ecutrho=ecutrho,
            kpoints=kpoints_nscf, spin_polarized=spin_polarized,
            occupations="tetrahedra",
        )
        nscf_file.write_text(nscf_input)

        nscf_result = runner_instance.run(
            executable="pw.x", input_file=nscf_file,
            output_file=nscf_out, work_dir=workflow_dir, nprocs=config.nprocs,
        )

        if nscf_result.in_progress:
            manifest = {
                "workflow_type": "dos", "workflow_id": workflow_id,
                "steps": ["scf", "nscf", "dos"], "step_idx": 1,
                "task_id": nscf_result.task_id, "output_file": "nscf.out",
                "runner": runner_used,
                "params": {
                    "structure": structure, "ecutwfc": ecutwfc, "ecutrho": ecutrho,
                    "kpoints_scf": kpoints_scf, "kpoints_nscf": kpoints_nscf,
                    "spin_polarized": spin_polarized, "emin": emin, "emax": emax,
                    "deltae": deltae_actual, "nprocs": config.nprocs,
                },
                "partial": {
                    "total_energy_eV": scf_parsed.total_energy_ev,
                    "fermi_energy_eV": scf_parsed.fermi_energy_ev,
                },
            }
            _save_manifest(workflow_dir, manifest)
            _register_workflow(config, workflow_id, nscf_result.task_id,
                               runner_used, "dos", workflow_dir, structure)
            return {
                "status": "submitted", "job_id": workflow_id,
                "current_step": "nscf", "output_dir": str(workflow_dir),
                "message": f"NSCF submitted (SCF cached). Poll with qe_get_status(job_id='{workflow_id}').",
                **results,
            }

        if not nscf_result.success:
            return {"success": False, "step_failed": "nscf",
                    "error": nscf_result.error_message, **results}

    # ---- Step 3: dos.x -----------------------------------------------------
    dos_out  = workflow_dir / "dos.out"
    dos_file = workflow_dir / "dos.in"
    dos_dat  = workflow_dir / "dos.dat"

    if not _postproc_step_done(workflow_dir, "dos.out", "dos.dat"):
        dos_input = generate_dos_input(
            prefix=workflow_id, outdir="./tmp", fildos="dos.dat",
            emin=emin, emax=emax, deltae=deltae_actual,
        )
        dos_file.write_text(dos_input)

        dos_result = runner_instance.run(
            executable="dos.x", input_file=dos_file,
            output_file=dos_out, work_dir=workflow_dir, nprocs=1,
        )

        if dos_result.in_progress:
            manifest = {
                "workflow_type": "dos", "workflow_id": workflow_id,
                "steps": ["scf", "nscf", "dos"], "step_idx": 2,
                "task_id": dos_result.task_id, "output_file": "dos.out",
                "runner": runner_used,
                "params": {
                    "structure": structure, "ecutwfc": ecutwfc, "ecutrho": ecutrho,
                    "kpoints_scf": kpoints_scf, "kpoints_nscf": kpoints_nscf,
                    "spin_polarized": spin_polarized, "emin": emin, "emax": emax,
                    "deltae": deltae_actual, "nprocs": config.nprocs,
                },
                "partial": {
                    "total_energy_eV": scf_parsed.total_energy_ev,
                    "fermi_energy_eV": scf_parsed.fermi_energy_ev,
                },
            }
            _save_manifest(workflow_dir, manifest)
            _register_workflow(config, workflow_id, dos_result.task_id,
                               runner_used, "dos", workflow_dir, structure)
            return {
                "status": "submitted", "job_id": workflow_id,
                "current_step": "dos", "output_dir": str(workflow_dir),
                "message": f"dos.x submitted (SCF+NSCF cached). Poll with qe_get_status(job_id='{workflow_id}').",
                **results,
            }

        if not dos_result.success:
            return {"success": False, "step_failed": "dos",
                    "error": dos_result.error_message, **results}

    if not dos_dat.exists():
        return {"success": False, "step_failed": "parse_dos",
                "error": "dos.dat not found", **results}

    dos_parsed = QEOutputParser.parse_dos(dos_dat)
    results.update({
        "success": True,
        "energies_eV": dos_parsed.energies,
        "dos": dos_parsed.dos,
        "integrated_dos": dos_parsed.integrated_dos,
        "dos_fermi_eV": dos_parsed.fermi_energy_ev,
        "energy_range_eV": [
            min(dos_parsed.energies) if dos_parsed.energies else None,
            max(dos_parsed.energies) if dos_parsed.energies else None,
        ],
        "n_points": len(dos_parsed.energies),
        "dos_file": str(dos_dat),
    })
    return results


# ---------------------------------------------------------------------------
# Workflow: relax + SCF
# ---------------------------------------------------------------------------

def workflow_relax_and_scf(
    structure: str,
    ecutwfc: float | None = None,
    ecutrho: float | None = None,
    kpoints: list[int] | None = None,
    variable_cell: bool | None = None,
    spin_polarized: bool | None = None,
    prefix: str | None = None,
    runner: str | None = None,
) -> dict[str, Any]:
    """
    Relax structure then perform accurate SCF.

    Steps are skipped when their output files already exist (resumable).
    With the Globus runner, submits the first pending step and returns
    a job_id; call qe_get_status(job_id) to advance.
    """
    config = QEConfig.from_environment()
    workflow_id = prefix or f"relax_scf_{uuid.uuid4().hex[:8]}"
    workflow_dir = config.workdir / workflow_id
    workflow_dir.mkdir(parents=True, exist_ok=True)

    atoms = load_structure(structure)
    elements = list(set(atoms.get_chemical_symbols()))

    spin_polarized  = spin_polarized if spin_polarized is not None else _detect_magnetic(atoms)
    variable_cell   = variable_cell if variable_cell is not None else False
    calc_type_relax = "vc-relax" if variable_cell else "relax"

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

    runner_instance = get_runner(config, runner_type=runner)
    runner_used = runner or os.environ.get("QE_RUNNER", "globus")
    results: dict = {"workflow_id": workflow_id, "output_dir": str(workflow_dir)}

    # ---- Step 1: Relaxation ------------------------------------------------
    relax_out  = workflow_dir / "relax.out"
    relax_file = workflow_dir / "relax.in"
    relax_parsed = None

    if _pw_step_done(workflow_dir, "relax.out", workflow_id):
        relax_parsed = QEOutputParser.parse_scf(relax_out.read_text(errors="replace"))
        results["relaxation"] = {
            "success": True,
            "converged": "End of BFGS" in relax_out.read_text(errors="replace"),
            "energy_eV": relax_parsed.total_energy_ev,
        }
    else:
        relax_input = generate_pw_input(
            atoms=atoms, pseudo_lib=pseudo_lib, calculation=calc_type_relax,
            prefix=workflow_id, ecutwfc=ecutwfc, ecutrho=ecutrho,
            kpoints=kpoints, spin_polarized=spin_polarized,
        )
        relax_file.write_text(relax_input)

        relax_result = runner_instance.run(
            executable="pw.x", input_file=relax_file,
            output_file=relax_out, work_dir=workflow_dir, nprocs=config.nprocs,
        )

        if relax_result.in_progress:
            manifest = {
                "workflow_type": "relax_scf", "workflow_id": workflow_id,
                "steps": ["relax", "scf"], "step_idx": 0,
                "task_id": relax_result.task_id, "output_file": "relax.out",
                "runner": runner_used,
                "params": {
                    "structure": structure, "ecutwfc": ecutwfc, "ecutrho": ecutrho,
                    "kpoints": kpoints, "spin_polarized": spin_polarized,
                    "variable_cell": variable_cell, "nprocs": config.nprocs,
                },
                "partial": {},
            }
            _save_manifest(workflow_dir, manifest)
            _register_workflow(config, workflow_id, relax_result.task_id,
                               runner_used, "relax_scf", workflow_dir, structure)
            return {
                "status": "submitted", "job_id": workflow_id,
                "current_step": "relax", "output_dir": str(workflow_dir),
                "message": f"Relax submitted. Poll with qe_get_status(job_id='{workflow_id}').",
            }

        relax_parsed = QEOutputParser.parse_scf(relax_result.stdout)
        results["relaxation"] = {
            "success": relax_result.success,
            "converged": "End of BFGS" in relax_result.stdout,
            "energy_eV": relax_parsed.total_energy_ev,
        }

        if not relax_result.success:
            return {"success": False, "step_failed": "relax",
                    "error": relax_result.error_message, **results}

    # ---- Step 2: Final SCF (tight convergence) -----------------------------
    scf_out  = workflow_dir / "scf.out"
    scf_file = workflow_dir / "scf.in"

    if not _pw_step_done(workflow_dir, "scf.out", workflow_id):
        scf_input = generate_pw_input(
            atoms=atoms,  # Uses original structure; wavefunctions from relax are reused
            pseudo_lib=pseudo_lib, calculation="scf",
            prefix=workflow_id, ecutwfc=ecutwfc, ecutrho=ecutrho,
            kpoints=kpoints, spin_polarized=spin_polarized,
            conv_thr=1.0e-8,
        )
        scf_file.write_text(scf_input)

        scf_result = runner_instance.run(
            executable="pw.x", input_file=scf_file,
            output_file=scf_out, work_dir=workflow_dir, nprocs=config.nprocs,
        )

        if scf_result.in_progress:
            manifest = {
                "workflow_type": "relax_scf", "workflow_id": workflow_id,
                "steps": ["relax", "scf"], "step_idx": 1,
                "task_id": scf_result.task_id, "output_file": "scf.out",
                "runner": runner_used,
                "params": {
                    "structure": structure, "ecutwfc": ecutwfc, "ecutrho": ecutrho,
                    "kpoints": kpoints, "spin_polarized": spin_polarized,
                    "variable_cell": variable_cell, "nprocs": config.nprocs,
                },
                "partial": {
                    "relax_energy_eV": relax_parsed.total_energy_ev if relax_parsed else None,
                },
            }
            _save_manifest(workflow_dir, manifest)
            _register_workflow(config, workflow_id, scf_result.task_id,
                               runner_used, "relax_scf", workflow_dir, structure)
            return {
                "status": "submitted", "job_id": workflow_id,
                "current_step": "scf", "output_dir": str(workflow_dir),
                "message": f"Final SCF submitted (relax cached). Poll with qe_get_status(job_id='{workflow_id}').",
                **results,
            }

        if not scf_result.success:
            return {"success": False, "step_failed": "scf",
                    "error": scf_result.error_message, **results}

        scf_parsed = QEOutputParser.parse_scf(scf_result.stdout)
    else:
        scf_parsed = QEOutputParser.parse_scf(scf_out.read_text(errors="replace"))

    results.update({
        "success": scf_parsed.converged,
        "total_energy_eV": scf_parsed.total_energy_ev,
        "total_energy_Ry": scf_parsed.total_energy_ry,
        "fermi_energy_eV": scf_parsed.fermi_energy_ev,
        "forces_eV_per_angstrom": scf_parsed.forces,
    })
    return results


# ---------------------------------------------------------------------------
# Workflow state machine advancement (called by job_status.py)
# ---------------------------------------------------------------------------

def advance_workflow(work_dir: Path, manifest: dict, runner_instance) -> dict:
    """
    Advance a workflow by one step: collect current Globus result, then submit
    the next step. Returns a status dict (pending / advancing / completed / failed).

    Called from tools/job_status.py on every qe_get_status() invocation.
    """
    from qe_mcp.core.globus_runner import GlobusComputeRunner

    if not isinstance(runner_instance, GlobusComputeRunner):
        return {"success": False, "error": "advance_workflow requires a Globus runner"}

    workflow_type = manifest["workflow_type"]
    step_idx = manifest["step_idx"]
    steps = manifest["steps"]
    workflow_id = manifest["workflow_id"]
    params = manifest["params"]
    config = QEConfig.from_environment()

    # Collect current step
    result = runner_instance.collect(
        manifest["task_id"], work_dir, manifest["output_file"]
    )

    if result.in_progress:
        gs = result.globus_status or "pending"
        if gs == "running":
            msg = f"Step '{steps[step_idx]}' is actively computing on Polaris nodes. Check back in ~5 minutes."
        else:
            msg = f"Step '{steps[step_idx]}' is waiting in the Polaris PBS queue. Could take minutes to hours."
        return {
            "status": "pending",
            "job_id": workflow_id,
            "current_step": steps[step_idx],
            "steps_remaining": steps[step_idx:],
            "queue_status": gs,
            "message": msg,
        }

    if not result.success:
        return {
            "success": False, "status": "failed",
            "job_id": workflow_id,
            "step_failed": steps[step_idx],
            "error": result.error_message,
        }

    # Step completed — update partial results
    current_step = steps[step_idx]
    partial = manifest.setdefault("partial", {})

    if current_step in ("scf", "relax"):
        parsed = QEOutputParser.parse_scf(result.stdout)
        partial["total_energy_eV"] = parsed.total_energy_ev
        partial["fermi_energy_eV"] = parsed.fermi_energy_ev
        if current_step == "relax":
            partial["relax_converged"] = "End of BFGS" in result.stdout

    step_idx += 1
    manifest["step_idx"] = step_idx

    if step_idx >= len(steps):
        return _finalize_workflow(work_dir, manifest, partial, workflow_type, config)

    # Submit next step
    next_step = steps[step_idx]
    atoms = load_structure(params["structure"])
    pseudo_lib = SG15Library(config.pseudo_dir)

    if workflow_type == "bandstructure":
        if next_step == "nscf":
            nscf_input = generate_pw_input(
                atoms=atoms, pseudo_lib=pseudo_lib, calculation="bands",
                prefix=workflow_id, ecutwfc=params["ecutwfc"], ecutrho=params["ecutrho"],
                kpoints_crystal=params["kpts"], spin_polarized=params["spin_polarized"],
                nbnd=params["nbnd"], nosym=True,
            )
            input_file = work_dir / "nscf.in"
            input_file.write_text(nscf_input)
            new_task_id = runner_instance._submit("pw.x", input_file, work_dir, params["nprocs"])
            manifest["task_id"] = new_task_id
            manifest["output_file"] = "nscf.out"
        elif next_step == "bands":
            bands_input = generate_bands_input(
                prefix=workflow_id, outdir="./tmp", filband="bands.dat",
            )
            input_file = work_dir / "bands.in"
            input_file.write_text(bands_input)
            new_task_id = runner_instance._submit("bands.x", input_file, work_dir, 1)
            manifest["task_id"] = new_task_id
            manifest["output_file"] = "bands.out"

    elif workflow_type == "dos":
        if next_step == "nscf":
            nscf_input = generate_pw_input(
                atoms=atoms, pseudo_lib=pseudo_lib, calculation="nscf",
                prefix=workflow_id, ecutwfc=params["ecutwfc"], ecutrho=params["ecutrho"],
                kpoints=params.get("kpoints_nscf"), spin_polarized=params["spin_polarized"],
                occupations="tetrahedra",
            )
            input_file = work_dir / "nscf.in"
            input_file.write_text(nscf_input)
            new_task_id = runner_instance._submit("pw.x", input_file, work_dir, params["nprocs"])
            manifest["task_id"] = new_task_id
            manifest["output_file"] = "nscf.out"
        elif next_step == "dos":
            dos_input = generate_dos_input(
                prefix=workflow_id, outdir="./tmp", fildos="dos.dat",
                emin=params.get("emin"), emax=params.get("emax"),
                deltae=params.get("deltae", 0.01),
            )
            input_file = work_dir / "dos.in"
            input_file.write_text(dos_input)
            new_task_id = runner_instance._submit("dos.x", input_file, work_dir, 1)
            manifest["task_id"] = new_task_id
            manifest["output_file"] = "dos.out"

    elif workflow_type == "relax_scf":
        if next_step == "scf":
            scf_input = generate_pw_input(
                atoms=atoms, pseudo_lib=pseudo_lib, calculation="scf",
                prefix=workflow_id, ecutwfc=params["ecutwfc"], ecutrho=params["ecutrho"],
                kpoints=params.get("kpoints"), spin_polarized=params["spin_polarized"],
                conv_thr=1.0e-8,
            )
            input_file = work_dir / "scf.in"
            input_file.write_text(scf_input)
            new_task_id = runner_instance._submit("pw.x", input_file, work_dir, params["nprocs"])
            manifest["task_id"] = new_task_id
            manifest["output_file"] = "scf.out"

    _save_manifest(work_dir, manifest)

    return {
        "status": "advancing",
        "job_id": workflow_id,
        "completed_step": current_step,
        "next_step": next_step,
        "message": f"'{current_step}' done. '{next_step}' submitted. Call qe_get_status again.",
    }


def _finalize_workflow(work_dir: Path, manifest: dict, partial: dict,
                       workflow_type: str, config: QEConfig) -> dict:
    """Parse final result from completed workflow files."""
    workflow_id = manifest["workflow_id"]
    params = manifest["params"]

    if workflow_type == "bandstructure":
        special_points = {k: v for k, v in params.get("special_points", {}).items()}
        result = _parse_band_results(
            work_dir, workflow_id, partial.get("fermi_energy_eV"), special_points,
        )
        result.update({
            "total_energy_eV": partial.get("total_energy_eV"),
            "fermi_energy_eV": partial.get("fermi_energy_eV"),
            "workflow_id": workflow_id,
            "status": "completed",
            "job_id": workflow_id,
        })
        return result

    elif workflow_type == "dos":
        dos_dat = work_dir / "dos.dat"
        if not dos_dat.exists():
            return {"success": False, "error": "dos.dat not found", "job_id": workflow_id}
        dos_parsed = QEOutputParser.parse_dos(dos_dat)
        return {
            "success": True, "status": "completed", "job_id": workflow_id,
            "workflow_id": workflow_id,
            "total_energy_eV": partial.get("total_energy_eV"),
            "fermi_energy_eV": partial.get("fermi_energy_eV"),
            "energies_eV": dos_parsed.energies,
            "dos": dos_parsed.dos,
            "integrated_dos": dos_parsed.integrated_dos,
            "dos_fermi_eV": dos_parsed.fermi_energy_ev,
            "n_points": len(dos_parsed.energies),
            "dos_file": str(dos_dat),
            "output_dir": str(work_dir),
        }

    elif workflow_type == "relax_scf":
        scf_out = work_dir / "scf.out"
        if not scf_out.exists():
            return {"success": False, "error": "scf.out not found", "job_id": workflow_id}
        scf_parsed = QEOutputParser.parse_scf(scf_out.read_text(errors="replace"))
        return {
            "success": scf_parsed.converged, "status": "completed", "job_id": workflow_id,
            "workflow_id": workflow_id,
            "total_energy_eV": scf_parsed.total_energy_ev,
            "total_energy_Ry": scf_parsed.total_energy_ry,
            "fermi_energy_eV": scf_parsed.fermi_energy_ev,
            "relaxation": {"converged": partial.get("relax_converged"),
                           "energy_eV": partial.get("relax_energy_eV")},
            "output_dir": str(work_dir),
        }

    return {"success": False, "error": f"Unknown workflow_type: {workflow_type}"}
