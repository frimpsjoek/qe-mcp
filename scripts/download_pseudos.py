#!/usr/bin/env python3
"""Download and extract SG15 ONCV pseudopotentials."""

import urllib.request
import tarfile
import ssl
from pathlib import Path

SG15_URL = "http://www.quantum-simulation.org/potentials/sg15_oncv/sg15_oncv_upf_2020-02-06.tar.gz"
PROJECT_ROOT = Path(__file__).parent.parent
PSEUDO_DIR = PROJECT_ROOT / "pseudopotentials" / "sg15_oncv"


def download_sg15():
    """Download and extract SG15 pseudopotentials."""

    PSEUDO_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    upf_files = list(PSEUDO_DIR.glob("*.upf"))
    if len(upf_files) > 50:  # SG15 has ~80+ elements
        print(f"✓ SG15 pseudopotentials already present ({len(upf_files)} files)")
        print(f"  Location: {PSEUDO_DIR}")
        return

    tarball = PSEUDO_DIR.parent / "sg15_oncv.tar.gz"

    # Download
    print(f"Downloading SG15 ONCV pseudopotentials...")
    print(f"  URL: {SG15_URL}")
    print(f"  This may take a minute...")

    try:
        # Try with SSL verification
        urllib.request.urlretrieve(SG15_URL, tarball)
    except Exception as e:
        print(f"  Standard download failed: {e}")
        print("  Trying without SSL verification...")
        # Fallback without SSL verification
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(SG15_URL, context=ctx) as response:
            with open(tarball, 'wb') as f:
                f.write(response.read())

    print(f"✓ Downloaded to {tarball}")

    # Extract
    print("Extracting...")
    with tarfile.open(tarball, "r:gz") as tar:
        # SG15 tarball has a subdirectory structure, extract UPF files
        for member in tar.getmembers():
            if member.name.endswith(".upf") or member.name.endswith(".UPF"):
                # Extract to flat directory
                member.name = Path(member.name).name
                tar.extract(member, PSEUDO_DIR)

    # Cleanup tarball
    tarball.unlink()

    upf_files = list(PSEUDO_DIR.glob("*.upf")) + list(PSEUDO_DIR.glob("*.UPF"))
    print(f"✓ Extracted {len(upf_files)} pseudopotential files")
    print(f"  Location: {PSEUDO_DIR}")

    # List a few
    print("\nSample files:")
    for f in sorted(upf_files)[:8]:
        print(f"  - {f.name}")
    if len(upf_files) > 8:
        print(f"  ... and {len(upf_files) - 8} more")


if __name__ == "__main__":
    download_sg15()
