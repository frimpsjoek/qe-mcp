"""Configuration management for QE MCP server."""

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class QEConfig:
    """Configuration for QE MCP server."""

    # Docker settings
    use_docker: bool = True
    docker_image: str = "qe-local"

    # QE executables (used if not using Docker)
    qe_prefix: Path | None = None
    pw_executable: str = "pw.x"
    pp_executable: str = "pp.x"
    bands_executable: str = "bands.x"
    dos_executable: str = "dos.x"
    projwfc_executable: str = "projwfc.x"

    # Parallelization
    nprocs: int = 1
    npool: int = 1

    # Directories
    pseudo_dir: Path = field(
        default_factory=lambda: Path(__file__).parent / "pseudopotentials"
    )
    workdir: Path = field(default_factory=lambda: Path.cwd() / "qe_calculations")

    # Defaults (will be overridden by pseudopotential hints)
    default_ecutwfc: float = 50.0
    default_ecutrho: float = 400.0
    default_kspacing: float = 0.04  # 1/Å for auto k-points

    @classmethod
    def from_environment(cls) -> "QEConfig":
        """Load config from environment variables."""
        pseudo_dir_default = Path(__file__).parent / "pseudopotentials"
        workdir_default = Path.cwd() / "qe_calculations"

        return cls(
            use_docker=os.environ.get("QE_USE_DOCKER", "true").lower() == "true",
            docker_image=os.environ.get("QE_DOCKER_IMAGE", "qe-local"),
            qe_prefix=(
                Path(os.environ["QE_PREFIX"]) if "QE_PREFIX" in os.environ else None
            ),
            nprocs=int(os.environ.get("QE_NPROCS", 1)),
            pseudo_dir=Path(os.environ.get("QE_PSEUDO_DIR", pseudo_dir_default)),
            workdir=Path(os.environ.get("QE_WORKDIR", workdir_default)),
        )

    def get_executable_path(self, name: str) -> str:
        """Get full path to a QE executable."""
        exe_map = {
            "pw": self.pw_executable,
            "pp": self.pp_executable,
            "bands": self.bands_executable,
            "dos": self.dos_executable,
            "projwfc": self.projwfc_executable,
        }
        exe = exe_map.get(name, f"{name}.x")

        if self.qe_prefix:
            return str(self.qe_prefix / exe)
        return exe
