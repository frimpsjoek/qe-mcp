"""
Data access tools for reading QE output files.

These tools allow LLMs to read raw data files from disk
for plotting and further analysis.
"""

from pathlib import Path
from typing import Any


def read_bands_gnu(file_path: str) -> dict[str, Any]:
    """
    Read band structure data from .gnu file (gnuplot format).
    
    The .gnu file contains k-distance and energy values that can be
    directly plotted as a band structure. Blank lines separate bands.
    
    Args:
        file_path: Path to the .gnu file (e.g., bands.dat.gnu)
        
    Returns:
        Dictionary containing:
        - success: Whether file was read successfully
        - n_bands: Number of bands
        - n_kpoints: Number of k-points per band
        - k_distances: List of k-distance values (x-axis for plotting)
        - bands: List of lists, each inner list is energies for one band
        - raw_data: The raw file content for custom parsing
        - plot_instruction: How to plot this data
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        content = path.read_text()
        lines = content.strip().split('\n')
        
        # Parse into bands (separated by blank lines)
        bands = []
        current_band = []
        k_distances = []
        
        for line in lines:
            line = line.strip()
            if not line:
                # Blank line = new band
                if current_band:
                    bands.append(current_band)
                    current_band = []
            else:
                parts = line.split()
                if len(parts) >= 2:
                    k_dist = float(parts[0])
                    energy = float(parts[1])
                    current_band.append(energy)
                    # Only store k_distances once (first band)
                    if len(bands) == 0:
                        k_distances.append(k_dist)
        
        # Don't forget last band
        if current_band:
            bands.append(current_band)
        
        return {
            "success": True,
            "n_bands": len(bands),
            "n_kpoints": len(k_distances),
            "k_distances": k_distances,
            "bands": bands,  # bands[band_idx][kpt_idx] = energy in eV
            "raw_data": content,
            "plot_instruction": (
                "To plot: use k_distances as x-axis, each band as y-values. "
                "Use Python matplotlib unless the user explicitly requests another format. "
                "Never default to JavaScript, Chart.js, Plotly, HTML canvas, or browser plotting."
            )
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def read_dos_dat(file_path: str) -> dict[str, Any]:
    """
    Read DOS data from .dat file.
    
    The DOS file contains energy and DOS values that can be
    directly plotted. First column is energy, second is DOS.
    
    Args:
        file_path: Path to the dos.dat file
        
    Returns:
        Dictionary containing:
        - success: Whether file was read successfully
        - n_points: Number of data points
        - energies: List of energy values (x-axis)
        - dos: List of DOS values (y-axis)
        - fermi_energy: Fermi energy if found in header
        - raw_data: Raw file content
        - plot_instruction: How to plot this data
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        content = path.read_text()
        lines = content.strip().split('\n')
        
        energies = []
        dos = []
        integrated_dos = []
        fermi_energy = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for Fermi energy in header
            if 'EFermi' in line or 'Fermi' in line:
                import re
                match = re.search(r'[-+]?\d*\.?\d+', line)
                if match:
                    fermi_energy = float(match.group())
                continue
            
            # Skip comment lines
            if line.startswith('#'):
                continue
                
            parts = line.split()
            if len(parts) >= 2:
                energies.append(float(parts[0]))
                dos.append(float(parts[1]))
                if len(parts) >= 3:
                    integrated_dos.append(float(parts[2]))
        
        return {
            "success": True,
            "n_points": len(energies),
            "energies": energies,
            "dos": dos,
            "integrated_dos": integrated_dos if integrated_dos else None,
            "fermi_energy": fermi_energy,
            "raw_data": content,
            "plot_instruction": (
                "To plot DOS: use energies as x-axis, dos as y-axis. "
                "Use Python matplotlib unless the user explicitly requests another format. "
                "Never default to JavaScript, Chart.js, Plotly, HTML canvas, or browser plotting."
            )
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def read_pdos_dat(file_path: str) -> dict[str, Any]:
    """
    Read projected DOS (PDOS) data from projwfc.x output.
    
    PDOS files contain energy and orbital-projected DOS values.
    
    Args:
        file_path: Path to the PDOS file (e.g., pwscf.pdos_atm#1(Si)_wfc#1(s))
        
    Returns:
        Dictionary containing:
        - success: Whether file was read successfully
        - atom_info: Atom and orbital information from filename
        - n_points: Number of data points
        - energies: Energy values
        - ldos: Local DOS values
        - pdos_columns: Additional PDOS columns if present
        - raw_data: Raw file content
        - plot_instruction: How to plot this data
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        content = path.read_text()
        lines = content.strip().split('\n')
        
        # Parse atom/orbital info from filename
        filename = path.name
        atom_info = filename  # Keep full name for reference
        
        energies = []
        ldos = []
        pdos_columns = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split()
            if len(parts) >= 2:
                energies.append(float(parts[0]))
                ldos.append(float(parts[1]))
                if len(parts) > 2:
                    pdos_columns.append([float(p) for p in parts[2:]])
        
        return {
            "success": True,
            "atom_info": atom_info,
            "n_points": len(energies),
            "energies": energies,
            "ldos": ldos,
            "pdos_columns": pdos_columns if pdos_columns else None,
            "raw_data": content,
            "plot_instruction": (
                "To plot PDOS: use energies as x-axis, ldos as y-axis. "
                "Use Python matplotlib unless the user explicitly requests another format. "
                "Never default to JavaScript, Chart.js, Plotly, HTML canvas, or browser plotting."
            )
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def list_calculation_files(output_dir: str) -> dict[str, Any]:
    """
    List all files in a calculation output directory.
    
    Helps LLMs discover what data files are available.
    
    Args:
        output_dir: Path to the calculation directory
        
    Returns:
        Dictionary with categorized file lists
    """
    try:
        path = Path(output_dir)
        if not path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {output_dir}"
            }
        
        files = list(path.iterdir())
        
        result = {
            "success": True,
            "directory": str(path),
            "band_files": [],
            "dos_files": [],
            "pdos_files": [],
            "input_files": [],
            "output_files": [],
            "other_files": [],
        }
        
        for f in files:
            if f.is_dir():
                continue
            name = f.name
            
            if name.endswith('.gnu'):
                result["band_files"].append(str(f))
            elif name.startswith('dos') and name.endswith('.dat'):
                result["dos_files"].append(str(f))
            elif 'pdos' in name:
                result["pdos_files"].append(str(f))
            elif name.endswith('.in'):
                result["input_files"].append(str(f))
            elif name.endswith('.out'):
                result["output_files"].append(str(f))
            else:
                result["other_files"].append(str(f))
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
