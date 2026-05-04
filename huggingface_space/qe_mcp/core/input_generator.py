"""
Input generation for Quantum ESPRESSO calculations.

Generates pw.x input files from atomic structures and parameters.
"""

from pathlib import Path
from ase import Atoms

from qe_mcp.core.pseudopotentials import SG15Library
from qe_mcp.core.structures import get_kpoints_grid


# Default starting magnetization for magnetic elements (in Bohr magnetons)
STARTING_MAGNETIZATION = {
    'Fe': 2.5,
    'Co': 1.5,
    'Ni': 1.0,
    'Mn': 3.0,
    'Cr': 2.0,
    'V': 1.0,
    'Gd': 7.0,
    'Eu': 7.0,
    'Tb': 5.0,
    'Dy': 5.0,
    'Ho': 4.0,
    'Er': 3.0,
}


# Default starting magnetization for magnetic elements (in Bohr magnetons)
STARTING_MAGNETIZATION = {
    'Fe': 2.5,
    'Co': 1.5,
    'Ni': 1.0,
    'Mn': 3.0,
    'Cr': 2.0,
    'V': 1.0,
    'Gd': 7.0,
    'Eu': 7.0,
    'Tb': 5.0,
    'Dy': 5.0,
    'Ho': 4.0,
    'Er': 3.0,
}


def generate_pw_input(
    atoms: Atoms,
    pseudo_lib: SG15Library,
    calculation: str = "scf",
    prefix: str = "calc",
    outdir: str = "./tmp",
    ecutwfc: float | None = None,
    ecutrho: float | None = None,
    kpoints: list[int] | None = None,
    kpoints_crystal: list[list[float]] | None = None,
    smearing: str | None = None,
    degauss: float = 0.02,
    occupations: str = "smearing",
    spin_polarized: bool = False,
    nbnd: int | None = None,
    conv_thr: float = 1.0e-6,
    forc_conv_thr: float = 1.0e-3,
    etot_conv_thr: float = 1.0e-4,
    press_conv_thr: float = 0.5,
    nstep: int = 100,
    cell_dofree: str = "all",
    mixing_beta: float = 0.7,
    electron_maxstep: int = 100,
    verbosity: str = "high",
    tprnfor: bool = True,
    tstress: bool = True,
    nosym: bool = False,
) -> str:
    """
    Generate pw.x input file content.

    Args:
        atoms: ASE Atoms object
        pseudo_lib: SG15Library instance
        calculation: 'scf', 'relax', 'vc-relax', 'nscf', 'bands'
        prefix: Calculation prefix for output files
        outdir: Output directory
        ecutwfc: Plane-wave cutoff (Ry), auto-determined if None
        ecutrho: Density cutoff (Ry), auto-determined if None
        kpoints: Monkhorst-Pack grid [n1, n2, n3]
        kpoints_crystal: Explicit k-points in crystal coordinates
        smearing: Smearing type ('gaussian', 'mv', 'mp', 'cold')
        degauss: Smearing width (Ry)
        occupations: 'smearing', 'fixed', 'tetrahedra'
        spin_polarized: Enable spin polarization
        nbnd: Number of bands
        conv_thr: SCF convergence threshold
        forc_conv_thr: Force convergence threshold for relax
        etot_conv_thr: Energy convergence threshold for relax
        press_conv_thr: Pressure convergence threshold for vc-relax
        nstep: Max relaxation steps
        cell_dofree: Cell DoF for vc-relax ('all', 'ibrav', 'x', 'y', 'z', etc.)
        mixing_beta: Mixing parameter for SCF
        electron_maxstep: Max SCF iterations
        verbosity: 'high' or 'low'
        tprnfor: Print forces
        tstress: Print stress
        nosym: Disable symmetry

    Returns:
        String containing complete pw.x input file
    """
    elements = list(set(atoms.get_chemical_symbols()))

    # Get pseudopotentials and cutoffs
    pseudos = pseudo_lib.to_qe_pseudopotentials(elements)
    if ecutwfc is None or ecutrho is None:
        rec_wfc, rec_rho = pseudo_lib.get_recommended_cutoffs(elements)
        ecutwfc = ecutwfc or rec_wfc
        ecutrho = ecutrho or rec_rho

    # Auto k-points if not provided
    if kpoints is None and kpoints_crystal is None:
        if calculation == "bands":
            # For bands, k-points should be provided explicitly
            raise ValueError("K-points must be provided for bands calculation")
        kpoints = get_kpoints_grid(atoms)

    # Determine smearing based on material type
    if smearing is None:
        smearing = "cold"  # Good general choice

    # Build input sections
    lines = []

    # CONTROL namelist
    lines.append("&CONTROL")
    lines.append(f"    calculation = '{calculation}'")
    lines.append(f"    prefix = '{prefix}'")
    lines.append(f"    outdir = '{outdir}'")
    lines.append(f"    pseudo_dir = './pseudo'")
    lines.append(f"    verbosity = '{verbosity}'")
    lines.append(f"    tprnfor = .{str(tprnfor).lower()}.")
    lines.append(f"    tstress = .{str(tstress).lower()}.")
    if calculation in ("relax", "vc-relax"):
        lines.append(f"    nstep = {nstep}")
        lines.append(f"    forc_conv_thr = {forc_conv_thr}")
        lines.append(f"    etot_conv_thr = {etot_conv_thr}")
    lines.append("/")
    lines.append("")

    # SYSTEM namelist
    lines.append("&SYSTEM")
    lines.append(f"    ibrav = 0")
    lines.append(f"    nat = {len(atoms)}")
    lines.append(f"    ntyp = {len(elements)}")
    lines.append(f"    ecutwfc = {ecutwfc}")
    lines.append(f"    ecutrho = {ecutrho}")
    lines.append(f"    occupations = '{occupations}'")
    if occupations == "smearing":
        lines.append(f"    smearing = '{smearing}'")
        lines.append(f"    degauss = {degauss}")
    if spin_polarized:
        lines.append("    nspin = 2")
        # Add starting magnetization for magnetic elements
        for i, el in enumerate(elements, 1):
            if el in STARTING_MAGNETIZATION:
                mag = STARTING_MAGNETIZATION[el]
                lines.append(f"    starting_magnetization({i}) = {mag}")
        # Add starting magnetization for magnetic elements
        for i, el in enumerate(elements, 1):
            if el in STARTING_MAGNETIZATION:
                mag = STARTING_MAGNETIZATION[el]
                lines.append(f"    starting_magnetization({i}) = {mag}")
    if nbnd is not None:
        lines.append(f"    nbnd = {nbnd}")
    if nosym:
        lines.append("    nosym = .true.")
    lines.append("/")
    lines.append("")

    # ELECTRONS namelist
    lines.append("&ELECTRONS")
    lines.append(f"    conv_thr = {conv_thr}")
    lines.append(f"    mixing_beta = {mixing_beta}")
    lines.append(f"    electron_maxstep = {electron_maxstep}")
    lines.append("/")
    lines.append("")

    # IONS namelist (for relax calculations)
    if calculation in ("relax", "vc-relax"):
        lines.append("&IONS")
        lines.append("    ion_dynamics = 'bfgs'")
        lines.append("/")
        lines.append("")

    # CELL namelist (for vc-relax)
    if calculation == "vc-relax":
        lines.append("&CELL")
        lines.append("    cell_dynamics = 'bfgs'")
        lines.append(f"    press_conv_thr = {press_conv_thr}")
        lines.append(f"    cell_dofree = '{cell_dofree}'")
        lines.append("/")
        lines.append("")

    # ATOMIC_SPECIES
    lines.append("ATOMIC_SPECIES")
    for el in elements:
        # Get atomic mass
        from ase.data import atomic_masses, atomic_numbers
        mass = atomic_masses[atomic_numbers[el]]
        lines.append(f"    {el} {mass:.6f} {pseudos[el]}")
    lines.append("")

    # CELL_PARAMETERS
    lines.append("CELL_PARAMETERS angstrom")
    cell = atoms.get_cell()
    for i in range(3):
        lines.append(f"    {cell[i, 0]:.10f} {cell[i, 1]:.10f} {cell[i, 2]:.10f}")
    lines.append("")

    # ATOMIC_POSITIONS
    lines.append("ATOMIC_POSITIONS angstrom")
    symbols = atoms.get_chemical_symbols()
    positions = atoms.get_positions()
    for sym, pos in zip(symbols, positions):
        lines.append(f"    {sym} {pos[0]:.10f} {pos[1]:.10f} {pos[2]:.10f}")
    lines.append("")

    # K_POINTS
    if kpoints_crystal is not None:
        # Explicit k-points (for bands)
        lines.append("K_POINTS crystal")
        lines.append(f"    {len(kpoints_crystal)}")
        for kpt in kpoints_crystal:
            if len(kpt) == 3:
                lines.append(f"    {kpt[0]:.10f} {kpt[1]:.10f} {kpt[2]:.10f} 1.0")
            else:
                lines.append(f"    {kpt[0]:.10f} {kpt[1]:.10f} {kpt[2]:.10f} {kpt[3]:.10f}")
    else:
        lines.append("K_POINTS automatic")
        lines.append(f"    {kpoints[0]} {kpoints[1]} {kpoints[2]} 0 0 0")
    lines.append("")

    return "\n".join(lines)


def generate_bands_input(
    prefix: str = "calc",
    outdir: str = "./tmp",
    filband: str = "bands.dat",
) -> str:
    """Generate bands.x input file."""
    lines = [
        "&BANDS",
        f"    prefix = '{prefix}'",
        f"    outdir = '{outdir}'",
        f"    filband = '{filband}'",
        "/",
        "",  # Trailing newline required by bands.x
    ]
    return "\n".join(lines)


def generate_dos_input(
    prefix: str = "calc",
    outdir: str = "./tmp",
    fildos: str = "dos.dat",
    emin: float | None = None,
    emax: float | None = None,
    deltae: float = 0.01,
) -> str:
    """Generate dos.x input file."""
    lines = [
        "&DOS",
        f"    prefix = '{prefix}'",
        f"    outdir = '{outdir}'",
        f"    fildos = '{fildos}'",
        f"    deltae = {deltae}",
    ]
    if emin is not None:
        lines.append(f"    emin = {emin}")
    if emax is not None:
        lines.append(f"    emax = {emax}")
    lines.append("/")
    lines.append("")  # Trailing newline required
    return "\n".join(lines)


def generate_projwfc_input(
    prefix: str = "calc",
    outdir: str = "./tmp",
    filpdos: str = "pdos",
    emin: float | None = None,
    emax: float | None = None,
    deltae: float = 0.01,
) -> str:
    """Generate projwfc.x input file."""
    lines = [
        "&PROJWFC",
        f"    prefix = '{prefix}'",
        f"    outdir = '{outdir}'",
        f"    filpdos = '{filpdos}'",
        f"    deltae = {deltae}",
    ]
    if emin is not None:
        lines.append(f"    emin = {emin}")
    if emax is not None:
        lines.append(f"    emax = {emax}")
    lines.append("/")
    lines.append("")  # Trailing newline required
    return "\n".join(lines)


def generate_pp_input(
    prefix: str = "calc",
    outdir: str = "./tmp",
    filplot: str = "charge.dat",
    plot_num: int = 0,
    spin_component: int = 0,
    kpoint: int | None = None,
    kband: int | None = None,
    iflag: int = 3,
    output_format: int = 6,
    fileout: str = "charge.cube",
    e1: tuple[float, float, float] = (1, 0, 0),
    e2: tuple[float, float, float] = (0, 1, 0),
    e3: tuple[float, float, float] = (0, 0, 1),
    nx: int = 50,
    ny: int = 50,
    nz: int = 50,
) -> str:
    """
    Generate pp.x input file.

    plot_num options:
        0 = charge density
        1 = total potential
        2 = local ionic potential
        3 = local potential
        4 = |psi|^2 (requires kpoint, kband)
        5 = |psi|^2 for STM
        6 = spin polarization
        7 = |psi|^2 summed over selected bands
        17 = PAW all-electron charge
    """
    lines = [
        "&INPUTPP",
        f"    prefix = '{prefix}'",
        f"    outdir = '{outdir}'",
        f"    filplot = '{filplot}'",
        f"    plot_num = {plot_num}",
    ]
    if spin_component != 0:
        lines.append(f"    spin_component = {spin_component}")
    if kpoint is not None:
        lines.append(f"    kpoint = {kpoint}")
    if kband is not None:
        lines.append(f"    kband = {kband}")
    lines.append("/")
    lines.append("")
    lines.append("&PLOT")
    lines.append(f"    iflag = {iflag}")
    lines.append(f"    output_format = {output_format}")
    lines.append(f"    fileout = '{fileout}'")
    if iflag == 3:  # 3D plot
        lines.append(f"    e1(1) = {e1[0]}, e1(2) = {e1[1]}, e1(3) = {e1[2]}")
        lines.append(f"    e2(1) = {e2[0]}, e2(2) = {e2[1]}, e2(3) = {e2[2]}")
        lines.append(f"    e3(1) = {e3[0]}, e3(2) = {e3[1]}, e3(3) = {e3[2]}")
        lines.append(f"    nx = {nx}, ny = {ny}, nz = {nz}")
    lines.append("/")
    return "\n".join(lines)
