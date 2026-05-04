"""
QE Output Parser.

Parse Quantum ESPRESSO output files to extract results.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SCFResult:
    """Results from an SCF calculation."""

    converged: bool
    total_energy_ry: float | None = None
    total_energy_ev: float | None = None
    fermi_energy_ev: float | None = None
    n_iterations: int | None = None
    total_force_ry_bohr: float | None = None
    total_magnetization: float | None = None
    absolute_magnetization: float | None = None
    walltime_seconds: float | None = None
    forces: list[list[float]] = field(default_factory=list)  # eV/Angstrom
    stress_kbar: list[list[float]] = field(default_factory=list)


@dataclass
class BandsResult:
    """Results from a bands calculation."""

    n_bands: int
    n_kpoints: int
    fermi_energy_ev: float | None
    band_gap_ev: float | None
    is_metal: bool
    vbm_ev: float | None = None
    cbm_ev: float | None = None
    kpoints: list[list[float]] = field(default_factory=list)
    eigenvalues: list[list[float]] = field(default_factory=list)  # [kpt][band]
    high_symmetry_points: dict[str, int] = field(default_factory=dict)


@dataclass
class DOSResult:
    """Results from a DOS calculation."""

    fermi_energy_ev: float
    energies: list[float] = field(default_factory=list)
    dos: list[float] = field(default_factory=list)
    integrated_dos: list[float] = field(default_factory=list)


# Conversion constants
RY_TO_EV = 13.605693122994


class QEOutputParser:
    """Parse Quantum ESPRESSO output files."""

    @staticmethod
    def parse_scf(output: str) -> SCFResult:
        """Parse pw.x SCF output."""
        result = SCFResult(converged=False)

        # Check convergence
        if "convergence has been achieved" in output:
            result.converged = True
        elif "convergence NOT achieved" in output:
            result.converged = False

        # Total energy (Ry)
        energy_match = re.search(
            r"!\s+total energy\s+=\s+([-\d.]+)\s+Ry", output
        )
        if energy_match:
            result.total_energy_ry = float(energy_match.group(1))
            result.total_energy_ev = result.total_energy_ry * RY_TO_EV

        # Fermi energy
        fermi_match = re.search(
            r"(?:the Fermi energy is|highest occupied level|Fermi energy:)\s+([-\d.]+)\s*ev",
            output,
            re.IGNORECASE,
        )
        if fermi_match:
            result.fermi_energy_ev = float(fermi_match.group(1))

        # Also check for "highest occupied, lowest unoccupied" format
        if result.fermi_energy_ev is None:
            ho_lu_match = re.search(
                r"highest occupied, lowest unoccupied level \(ev\):\s+([-\d.]+)\s+([-\d.]+)",
                output,
            )
            if ho_lu_match:
                # Use midpoint as approximate Fermi energy
                ho = float(ho_lu_match.group(1))
                lu = float(ho_lu_match.group(2))
                result.fermi_energy_ev = (ho + lu) / 2

        # Number of iterations
        iter_match = re.search(
            r"convergence has been achieved in\s+(\d+)\s+iterations", output
        )
        if iter_match:
            result.n_iterations = int(iter_match.group(1))

        # Total force
        force_match = re.search(
            r"Total force\s+=\s+([-\d.]+)", output
        )
        if force_match:
            result.total_force_ry_bohr = float(force_match.group(1))

        # Magnetization
        mag_match = re.search(
            r"total magnetization\s+=\s+([-\d.]+)", output
        )
        if mag_match:
            result.total_magnetization = float(mag_match.group(1))

        abs_mag_match = re.search(
            r"absolute magnetization\s+=\s+([-\d.]+)", output
        )
        if abs_mag_match:
            result.absolute_magnetization = float(abs_mag_match.group(1))

        # Parse forces on atoms
        forces_section = re.search(
            r"Forces acting on atoms.*?Total force",
            output,
            re.DOTALL,
        )
        if forces_section:
            force_lines = re.findall(
                r"atom\s+\d+\s+type\s+\d+\s+force\s+=\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)",
                forces_section.group(0),
            )
            # Convert from Ry/Bohr to eV/Angstrom
            ry_bohr_to_ev_ang = RY_TO_EV / 0.529177249
            result.forces = [
                [float(fx) * ry_bohr_to_ev_ang,
                 float(fy) * ry_bohr_to_ev_ang,
                 float(fz) * ry_bohr_to_ev_ang]
                for fx, fy, fz in force_lines
            ]

        # Parse stress tensor
        stress_match = re.search(
            r"total\s+stress.*?\n"
            r"\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\n"
            r"\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\n"
            r"\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)",
            output,
        )
        if stress_match:
            # First 3 columns are Ry/bohr^3, last 3 are kbar
            result.stress_kbar = [
                [float(stress_match.group(4)), float(stress_match.group(5)), float(stress_match.group(6))],
                [float(stress_match.group(10)), float(stress_match.group(11)), float(stress_match.group(12))],
                [float(stress_match.group(16)), float(stress_match.group(17)), float(stress_match.group(18))],
            ]

        # Walltime
        wall_match = re.search(
            r"PWSCF\s+:\s+[\dhms.]+\s+CPU\s+([\dhms.]+)\s+WALL", output
        )
        if wall_match:
            result.walltime_seconds = QEOutputParser._parse_time(wall_match.group(1))

        return result

    @staticmethod
    def parse_bands_dat(bands_file: Path, fermi_energy: float | None = None) -> BandsResult:
        """
        Parse bands.x output file (bands.dat or similar).

        The format is:
        &plot nbnd= X, nks= Y /
        k1 k2 k3
        e1 e2 e3 ... (10 per line)
        k1 k2 k3
        e1 e2 e3 ...
        """
        content = bands_file.read_text()

        # Parse header
        header_match = re.search(r"nbnd=\s*(\d+),\s*nks=\s*(\d+)", content)
        if not header_match:
            raise ValueError("Could not parse bands file header")

        n_bands = int(header_match.group(1))
        n_kpoints = int(header_match.group(2))

        # Parse data
        lines = content.strip().split("\n")[1:]  # Skip header line
        kpoints = []
        eigenvalues = []

        i = 0
        while i < len(lines):
            # K-point line
            kpt_line = lines[i].strip()
            if not kpt_line:
                i += 1
                continue

            kpt = [float(x) for x in kpt_line.split()]
            if len(kpt) == 3:
                kpoints.append(kpt)

                # Eigenvalue lines (10 values per line)
                i += 1
                eigs = []
                while len(eigs) < n_bands and i < len(lines):
                    eig_line = lines[i].strip()
                    if eig_line:
                        eigs.extend([float(x) for x in eig_line.split()])
                    i += 1

                eigenvalues.append(eigs[:n_bands])
            else:
                i += 1

        # Calculate band gap
        is_metal = True
        band_gap = None
        vbm = None
        cbm = None

        if fermi_energy is not None:
            # Find VBM and CBM
            all_below_fermi = []
            all_above_fermi = []

            for kpt_eigs in eigenvalues:
                for e in kpt_eigs:
                    if e <= fermi_energy:
                        all_below_fermi.append(e)
                    else:
                        all_above_fermi.append(e)

            if all_below_fermi and all_above_fermi:
                vbm = max(all_below_fermi)
                cbm = min(all_above_fermi)
                band_gap = cbm - vbm
                is_metal = band_gap < 0.01  # Small threshold for numerical noise

        return BandsResult(
            n_bands=n_bands,
            n_kpoints=n_kpoints,
            fermi_energy_ev=fermi_energy,
            band_gap_ev=band_gap if not is_metal else None,
            is_metal=is_metal,
            vbm_ev=vbm,
            cbm_ev=cbm,
            kpoints=kpoints,
            eigenvalues=eigenvalues,
        )

    @staticmethod
    def parse_dos(dos_file: Path) -> DOSResult:
        """Parse dos.x output file."""
        content = dos_file.read_text()
        lines = content.strip().split("\n")

        # First line usually has Fermi energy
        fermi_match = re.search(r"EFermi\s*=\s*([-\d.]+)", lines[0])
        fermi_energy = float(fermi_match.group(1)) if fermi_match else 0.0

        energies = []
        dos = []
        integrated_dos = []

        for line in lines[1:]:
            if line.strip() and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 2:
                    energies.append(float(parts[0]))
                    dos.append(float(parts[1]))
                    if len(parts) >= 3:
                        integrated_dos.append(float(parts[2]))

        return DOSResult(
            fermi_energy_ev=fermi_energy,
            energies=energies,
            dos=dos,
            integrated_dos=integrated_dos,
        )

    @staticmethod
    def _parse_time(time_str: str) -> float:
        """Parse QE time format (e.g., '1h 2m 3.45s' or '45.2s') to seconds."""
        total = 0.0

        hours = re.search(r"(\d+)h", time_str)
        if hours:
            total += int(hours.group(1)) * 3600

        minutes = re.search(r"(\d+)m", time_str)
        if minutes:
            total += int(minutes.group(1)) * 60

        seconds = re.search(r"([\d.]+)s", time_str)
        if seconds:
            total += float(seconds.group(1))

        return total
