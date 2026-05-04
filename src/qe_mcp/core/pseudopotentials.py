"""
SG15 ONCV Pseudopotential Library Manager.

Manages the SG15 norm-conserving pseudopotentials for Quantum ESPRESSO.
"""

from pathlib import Path
import re
from dataclasses import dataclass


@dataclass
class PseudoInfo:
    """Information about a pseudopotential file."""

    element: str
    path: Path
    filename: str
    ecutwfc_hint: float  # Recommended cutoff (Ry)
    ecutrho_hint: float  # Recommended density cutoff (Ry)
    xc: str = "PBE"
    pp_type: str = "ONCV"


class SG15Library:
    """
    Manager for SG15 ONCV pseudopotential library.

    File naming patterns in SG15:
    - {Element}_ONCV_PBE-1.0.upf
    - {Element}_ONCV_PBE-1.1.upf (some elements have versions)
    - {Element}_ONCV_PBE_FR-1.0.upf (fully relativistic)
    """

    # SG15 recommended cutoffs (Ry) - conservative values
    # Format: element -> (ecutwfc, ecutrho)
    # ecutrho = 4 * ecutwfc for norm-conserving pseudopotentials
    DEFAULT_CUTOFFS: dict[str, tuple[float, float]] = {
        # Period 1
        "H": (40, 160),
        "He": (40, 160),
        # Period 2
        "Li": (40, 160),
        "Be": (50, 200),
        "B": (40, 160),
        "C": (50, 200),
        "N": (60, 240),
        "O": (60, 240),
        "F": (60, 240),
        "Ne": (60, 240),
        # Period 3
        "Na": (40, 160),
        "Mg": (40, 160),
        "Al": (30, 120),
        "Si": (30, 120),
        "P": (30, 120),
        "S": (40, 160),
        "Cl": (50, 200),
        "Ar": (50, 200),
        # Period 4
        "K": (40, 160),
        "Ca": (40, 160),
        "Sc": (50, 200),
        "Ti": (50, 200),
        "V": (50, 200),
        "Cr": (50, 200),
        "Mn": (60, 240),
        "Fe": (60, 240),
        "Co": (60, 240),
        "Ni": (60, 240),
        "Cu": (60, 240),
        "Zn": (60, 240),
        "Ga": (50, 200),
        "Ge": (50, 200),
        "As": (50, 200),
        "Se": (50, 200),
        "Br": (40, 160),
        "Kr": (40, 160),
        # Period 5
        "Rb": (30, 120),
        "Sr": (30, 120),
        "Y": (40, 160),
        "Zr": (40, 160),
        "Nb": (50, 200),
        "Mo": (50, 200),
        "Tc": (50, 200),
        "Ru": (50, 200),
        "Rh": (50, 200),
        "Pd": (50, 200),
        "Ag": (50, 200),
        "Cd": (50, 200),
        "In": (40, 160),
        "Sn": (40, 160),
        "Sb": (40, 160),
        "Te": (40, 160),
        "I": (40, 160),
        "Xe": (40, 160),
        # Period 6
        "Cs": (30, 120),
        "Ba": (30, 120),
        "La": (50, 200),
        "Hf": (50, 200),
        "Ta": (50, 200),
        "W": (50, 200),
        "Re": (50, 200),
        "Os": (50, 200),
        "Ir": (50, 200),
        "Pt": (50, 200),
        "Au": (50, 200),
        "Hg": (50, 200),
        "Tl": (40, 160),
        "Pb": (40, 160),
        "Bi": (40, 160),
        "Po": (40, 160),
        "At": (40, 160),
        "Rn": (40, 160),
    }
    DEFAULT_CUTOFF = (60, 240)  # Fallback

    def __init__(self, pseudo_dir: Path | str):
        self.pseudo_dir = Path(pseudo_dir)
        self._index: dict[str, PseudoInfo] = {}
        self._scan_library()

    def _scan_library(self):
        """Scan directory and index all pseudopotentials."""
        if not self.pseudo_dir.exists():
            raise FileNotFoundError(
                f"Pseudopotential directory not found: {self.pseudo_dir}\n"
                f"Run: python scripts/download_pseudos.py"
            )

        # Pattern: Element_ONCV_PBE-1.0.upf or Element_ONCV_PBE_FR-1.0.upf
        pattern = re.compile(r"^([A-Z][a-z]?)_ONCV_PBE.*\.upf$", re.IGNORECASE)

        for upf_file in self.pseudo_dir.glob("*.upf"):
            match = pattern.match(upf_file.name)
            if match:
                element = match.group(1).capitalize()
                # Prefer non-FR (scalar relativistic) over FR (fully relativistic)
                if element not in self._index or "_FR" not in upf_file.name:
                    cutoffs = self.DEFAULT_CUTOFFS.get(element, self.DEFAULT_CUTOFF)
                    self._index[element] = PseudoInfo(
                        element=element,
                        path=upf_file.absolute(),
                        filename=upf_file.name,
                        ecutwfc_hint=cutoffs[0],
                        ecutrho_hint=cutoffs[1],
                    )

    def get(self, element: str) -> PseudoInfo:
        """Get pseudopotential info for an element."""
        element = element.capitalize()
        if element not in self._index:
            available = ", ".join(sorted(self._index.keys()))
            raise ValueError(
                f"No pseudopotential for '{element}'. Available: {available}"
            )
        return self._index[element]

    def get_for_atoms(self, elements: list[str]) -> dict[str, PseudoInfo]:
        """Get pseudopotentials for a list of elements."""
        return {el: self.get(el) for el in set(elements)}

    def get_recommended_cutoffs(self, elements: list[str]) -> tuple[float, float]:
        """
        Get recommended cutoffs for a set of elements.
        Returns the maximum required by any element.
        """
        pseudos = self.get_for_atoms(elements)
        ecutwfc = max(p.ecutwfc_hint for p in pseudos.values())
        ecutrho = max(p.ecutrho_hint for p in pseudos.values())
        return (ecutwfc, ecutrho)

    def list_available(self) -> list[str]:
        """List all available elements."""
        return sorted(self._index.keys())

    def to_qe_pseudopotentials(self, elements: list[str]) -> dict[str, str]:
        """
        Generate pseudopotentials dict for ASE Espresso calculator.
        Returns: {"Si": "Si_ONCV_PBE-1.2.upf", ...}
        """
        return {el: self.get(el).filename for el in set(elements)}

    def get_pseudo_dir(self) -> Path:
        """Get the pseudopotential directory path."""
        return self.pseudo_dir
