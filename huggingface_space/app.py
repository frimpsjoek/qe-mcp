"""
Quantum ESPRESSO MCP Server - HuggingFace Spaces Demo

A demonstration interface for the QE-MCP server that enables
LLMs to run DFT calculations with natural language.

This app includes:
1. A Gradio demo interface for interactive testing
2. The full MCP server with SSE transport for Claude/LLM integration
"""

import os
import sys
import json
import threading

import gradio as gr

# Add the qe_mcp package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# Demo Data (for Gradio interface when Docker is not available)
# =============================================================================

DEMO_RESULTS = {
    "Si": {
        "scf": {
            "success": True,
            "total_energy_eV": -214.4906,
            "fermi_energy_eV": 6.2975,
            "converged": True,
            "n_iterations": 4,
            "parameters_used": {"spin_polarized": False, "smearing": "cold", "degauss": 0.02}
        },
        "bandstructure": {
            "success": True,
            "band_gap_eV": 0.56,
            "is_direct": False,
            "vbm_location": "Γ",
            "cbm_location": "X",
            "fermi_energy_eV": 6.2975
        }
    },
    "Fe": {
        "scf": {
            "success": True,
            "total_energy_eV": -3220.5287,
            "fermi_energy_eV": 17.8432,
            "total_magnetization": 7.63,
            "converged": True,
            "n_iterations": 12,
            "parameters_used": {"spin_polarized": True, "smearing": "cold", "degauss": 0.02}
        }
    },
    "Cu": {
        "scf": {
            "success": True,
            "total_energy_eV": -1653.2341,
            "fermi_energy_eV": 12.4521,
            "converged": True,
            "n_iterations": 6,
            "parameters_used": {"spin_polarized": False, "smearing": "cold", "degauss": 0.02}
        }
    },
    "GaAs": {
        "scf": {
            "success": True,
            "total_energy_eV": -312.8765,
            "fermi_energy_eV": 5.1234,
            "converged": True,
            "n_iterations": 5,
            "parameters_used": {"spin_polarized": False, "smearing": "cold", "degauss": 0.02}
        },
        "bandstructure": {
            "success": True,
            "band_gap_eV": 0.48,
            "is_direct": True,
            "vbm_location": "Γ",
            "cbm_location": "Γ",
            "fermi_energy_eV": 5.1234
        }
    }
}

AVAILABLE_ELEMENTS = [
    "Ag", "Al", "Ar", "As", "Au", "B", "Ba", "Be", "Bi", "Br", "C", "Ca", "Cd", "Cl", 
    "Co", "Cr", "Cs", "Cu", "F", "Fe", "Ga", "Ge", "H", "He", "Hf", "Hg", "I", "In", 
    "Ir", "K", "Kr", "La", "Li", "Mg", "Mn", "Mo", "N", "Na", "Nb", "Ne", "Ni", "O", 
    "Os", "P", "Pb", "Pd", "Pt", "Rb", "Re", "Rh", "Ru", "S", "Sb", "Sc", "Se", "Si", 
    "Sn", "Sr", "Ta", "Tc", "Te", "Ti", "Tl", "V", "W", "Xe", "Y", "Zn", "Zr"
]

# =============================================================================
# MCP Tools Documentation
# =============================================================================

MCP_TOOLS = """
## 🔧 Available MCP Tools

### ⚡ Core Calculations

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `qe_run_scf` | Self-consistent field calculation | `structure`, `ecutwfc`, `ecutrho`, `kpoints`, `spin_polarized` |
| `qe_run_relax` | Optimize atomic positions (fixed cell) | `structure`, `forc_conv_thr`, `nstep` |
| `qe_run_vc_relax` | Variable-cell relaxation | `structure`, `press_conv_thr`, `cell_dofree` |

### 📊 Post-processing

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `qe_run_bands` | Extract band structure from NSCF | `scf_dir`, `prefix` |
| `qe_run_dos` | Calculate density of states | `scf_dir`, `emin`, `emax`, `deltae` |
| `qe_run_pdos` | Projected DOS (orbital-resolved) | `scf_dir`, `emin`, `emax` |

### 🔄 Workflows (Multi-step)

| Tool | Description | Steps |
|------|-------------|-------|
| `qe_workflow_bandstructure` | Complete band structure | SCF → NSCF bands → bands.x |
| `qe_workflow_dos` | Complete DOS calculation | SCF → NSCF (dense k) → dos.x |
| `qe_workflow_relax_and_scf` | Relax then accurate SCF | relax/vc-relax → SCF |

### 🛠️ Utilities

| Tool | Description | Returns |
|------|-------------|---------|
| `qe_load_structure` | Load/validate structure | formula, n_atoms, cell, positions |
| `qe_get_kpath` | High-symmetry k-path | kpoints, special_points, path_labels |
| `qe_suggest_kpoints` | Suggest MP k-grid | kpoints, recommendation |
| `qe_list_pseudopotentials` | List available elements | 69 elements with cutoffs |
| `qe_validate_structure` | Check for issues | errors, warnings, recommendations |
| `qe_status` | Server status | config, runner, pseudopotentials |

### 📁 Data Access

| Tool | Description | Returns |
|------|-------------|---------|
| `qe_read_bands` | Read bands.dat.gnu | k_distances, bands[], plot_instruction |
| `qe_read_dos` | Read dos.dat | energies, dos, fermi_energy |
| `qe_read_pdos` | Read PDOS files | energies, ldos, atom_info |
| `qe_list_files` | List calculation files | categorized file lists |
"""

# =============================================================================
# Demo Functions
# =============================================================================

def run_scf_demo(material: str) -> str:
    """Simulate SCF calculation"""
    material = material.strip()
    if material in DEMO_RESULTS:
        result = DEMO_RESULTS[material]["scf"]
        output = f"""## ⚡ SCF Calculation: {material}

✅ **Success**: {result['success']}
🔋 **Total Energy**: {result['total_energy_eV']:.4f} eV
📊 **Fermi Energy**: {result['fermi_energy_eV']:.4f} eV
🔄 **Converged**: {result['converged']} ({result['n_iterations']} iterations)
"""
        if result.get('total_magnetization'):
            output += f"🧲 **Magnetization**: {result['total_magnetization']:.2f} μB\n"
        output += f"\n⚙️ **Auto-detected parameters**: {json.dumps(result['parameters_used'])}"
        return output
    else:
        return f"""## ⚡ SCF Calculation: {material}

This is a **demo** showing the MCP tool interface.

In the full version, calling `qe_run_scf(structure='{material}')` would:
1. Build the crystal structure using ASE
2. Generate QE input files
3. Run pw.x in Docker container
4. Parse and return results

**Supported elements**: {', '.join(AVAILABLE_ELEMENTS)}
"""

def run_bandstructure_demo(material: str) -> str:
    """Simulate band structure calculation"""
    material = material.strip()
    if material in DEMO_RESULTS and "bandstructure" in DEMO_RESULTS[material]:
        result = DEMO_RESULTS[material]["bandstructure"]
        gap_type = "direct" if result['is_direct'] else "indirect"
        return f"""## 📈 Band Structure: {material}

✅ **Success**: {result['success']}
🎯 **Band Gap**: {result['band_gap_eV']:.2f} eV ({gap_type})
📍 **VBM Location**: {result['vbm_location']}
📍 **CBM Location**: {result['cbm_location']}
📊 **Fermi Energy**: {result['fermi_energy_eV']:.4f} eV

### Interpretation
{"This is a **semiconductor** with a " + gap_type + " band gap." if result['band_gap_eV'] > 0 else "This is a **metal**."}
"""
    else:
        return f"""## 📈 Band Structure: {material}

This is a **demo** showing the MCP tool interface.

In the full version, calling `qe_workflow_bandstructure(structure='{material}')` would:
1. Run SCF calculation
2. Get high-symmetry k-path (Γ-X-W-K-Γ-L-U-W-L-K)
3. Calculate bands along path
4. Analyze band gap

**Try**: Si, GaAs (have demo results)
"""

def show_mcp_config() -> str:
    """Show MCP configuration for Claude Desktop"""
    return """## 🔧 Claude Desktop Configuration

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "quantum-espresso": {
      "command": "uv",
      "args": ["--directory", "/path/to/QE_MCP", "run", "qe-mcp"]
    }
  }
}
```

Then restart Claude Desktop and you can say:
- *"Calculate the total energy of silicon"*
- *"What's the band gap of GaAs?"*
- *"Run a spin-polarized calculation for iron"*

---

## 🌐 Use with HuggingFace Space (SSE Transport)

Connect to this MCP server remotely using SSE transport:

```json
{
  "mcpServers": {
    "quantum-espresso": {
      "transport": "sse",
      "url": "https://YOUR_SPACE_NAME.hf.space/mcp/sse"
    }
  }
}
```

---

## 📋 Local Installation

### 1. Clone & Install
```bash
git clone https://github.com/frimpsjoe/QE_MCP.git
cd QE_MCP
uv sync
```

### 2. Download Pseudopotentials
```bash
python scripts/download_pseudos.py
```

### 3. Build Docker Image
```bash
docker build -t qe-local .
```

### 4. Configure Claude Desktop
Add the MCP server config (see above), then restart Claude.

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QE_USE_DOCKER` | `true` | Use Docker runner |
| `QE_DOCKER_IMAGE` | `qe-local` | Docker image name |
| `QE_NPROCS` | `1` | Parallel processes |
| `QE_WORKDIR` | `./qe_calculations` | Output directory |
| `QE_PSEUDO_DIR` | `./pseudopotentials` | Pseudopotential path |

---

## 🐳 Docker Image

The Dockerfile builds Quantum ESPRESSO v6.7MaX with:
- `pw.x` - Main DFT code
- `bands.x` - Band structure extraction
- `dos.x` - Density of states
- `projwfc.x` - Projected DOS
"""

def list_elements() -> str:
    """List all available elements"""
    elements_grid = ""
    for i, elem in enumerate(AVAILABLE_ELEMENTS):
        elements_grid += f"`{elem}` "
        if (i + 1) % 10 == 0:
            elements_grid += "\n"
    
    return f"""## 🧪 Supported Elements (69 total)

SG15 ONCV Pseudopotential Library:

{elements_grid}

### Magnetic Elements (auto spin-polarized)
`Fe` `Co` `Ni` `Mn` `Cr` `V` `Gd` `Eu` `Tb` `Dy` `Ho` `Er`
"""

def get_server_status() -> str:
    """Get MCP server status"""
    try:
        from qe_mcp.config import QEConfig
        config = QEConfig.from_environment()
        
        status = {
            "use_docker": config.use_docker,
            "docker_image": config.docker_image,
            "nprocs": config.nprocs,
            "workdir": str(config.workdir),
            "pseudo_dir": str(config.pseudo_dir),
        }
        
        # Check if Docker is available
        docker_available = False
        try:
            import subprocess
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            docker_available = result.returncode == 0
        except:
            pass
        
        status_md = f"""## 🖥️ MCP Server Status

| Setting | Value |
|---------|-------|
| Docker Mode | `{config.use_docker}` |
| Docker Available | `{docker_available}` |
| Docker Image | `{config.docker_image}` |
| Processes | `{config.nprocs}` |
| Work Directory | `{config.workdir}` |
| Pseudo Directory | `{config.pseudo_dir}` |

### MCP Server Endpoints
- **SSE**: `/mcp/sse` (for remote LLM connections)
- **Messages**: `/mcp/messages` (for MCP protocol)
"""
        return status_md
    except Exception as e:
        return f"## ⚠️ Error getting status\n\n`{str(e)}`"

# =============================================================================
# Gradio Interface
# =============================================================================

def create_gradio_app():
    """Create the Gradio interface"""
    with gr.Blocks(
        title="⚛️ Quantum ESPRESSO MCP Server",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="purple"),
        css="""
        .gradio-container { max-width: 1200px !important; }
        .tool-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 8px 0; }
        """
    ) as demo:
        gr.Markdown("""
        # ⚛️ Quantum ESPRESSO MCP Server
        
        > **Run DFT calculations with natural language!** An MCP server that enables LLMs to perform 
        > first-principles quantum mechanical simulations.
        
        [![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
        [![Quantum ESPRESSO](https://img.shields.io/badge/QE-v6.7-green)](https://www.quantum-espresso.org/)
        
        ⚠️ **Note**: This is a demo interface. For full calculations, run locally with Docker.
        
        🔗 **MCP Endpoint**: Connect to `/mcp/sse` for SSE transport
        """)
        
        with gr.Tabs():
            with gr.Tab("🧪 Try It"):
                gr.Markdown("### Simulate MCP Tool Calls")
                
                with gr.Row():
                    with gr.Column():
                        material_input = gr.Textbox(
                            label="Material Formula",
                            placeholder="Si, Fe, Cu, GaAs...",
                            value="Si"
                        )
                        with gr.Row():
                            scf_btn = gr.Button("⚡ Run SCF", variant="primary")
                            band_btn = gr.Button("📈 Band Structure", variant="secondary")
                    
                    with gr.Column():
                        output = gr.Markdown(label="Result")
                
                scf_btn.click(run_scf_demo, inputs=[material_input], outputs=[output])
                band_btn.click(run_bandstructure_demo, inputs=[material_input], outputs=[output])
                
                gr.Markdown("**Demo materials**: Si, Fe, Cu, GaAs")
            
            with gr.Tab("🔧 MCP Tools"):
                gr.Markdown(MCP_TOOLS)
                
                gr.Markdown("""
                ### 📋 Tool Details
                
                #### `qe_run_scf` - Self-Consistent Field Calculation
                ```python
                # All parameters except 'structure' are optional - smart defaults applied
                result = qe_run_scf(
                    structure="Si",           # Formula, CIF file, or POSCAR
                    ecutwfc=None,             # Plane-wave cutoff (Ry) - auto from pseudos
                    ecutrho=None,             # Density cutoff (Ry) - auto = 4x ecutwfc
                    kpoints=None,             # [n1, n2, n3] - auto based on cell size
                    smearing="cold",          # Marzari-Vanderbilt (good default)
                    degauss=0.02,             # Smearing width (Ry)
                    spin_polarized=None,      # Auto for Fe, Co, Ni, Mn...
                    conv_thr=1.0e-6,          # SCF convergence threshold
                    mixing_beta=0.7,          # Charge mixing parameter
                )
                # Returns: total_energy_eV, fermi_energy_eV, converged, magnetization...
                ```
                
                #### `qe_workflow_bandstructure` - Complete Band Structure
                ```python
                result = qe_workflow_bandstructure(
                    structure="GaAs",         # Any structure format
                    npoints_band=100,         # K-points along high-symmetry path
                    nbnd=None,                # Bands to compute (default: 8 per atom)
                    relax_first=False,        # Relax geometry first?
                )
                # Returns: band_gap_eV, is_direct_gap, vbm_eV, cbm_eV, 
                #          eigenvalues_eV[][], high_symmetry_points...
                ```
                
                #### `qe_workflow_dos` - Density of States
                ```python
                result = qe_workflow_dos(
                    structure="Fe",
                    kpoints_scf=[8, 8, 8],    # SCF k-grid
                    kpoints_nscf=None,        # NSCF k-grid (default: 2x SCF)
                    emin=-10.0,               # Energy range (eV from Fermi)
                    emax=10.0,
                    deltae=0.01,              # Energy step (eV)
                )
                # Returns: energies_eV[], dos[], fermi_energy_eV...
                ```
                
                ---
                
                ### 🎯 8 Prompts for Guided Workflows
                
                | Prompt | Description |
                |--------|-------------|
                | `band_structure` | Calculate electronic band structure |
                | `dos_calculation` | Density of states workflow |
                | `geometry_optimization` | Structure relaxation steps |
                | `convergence_test` | Parameter convergence testing |
                | `surface_calculation` | Surface energy calculations |
                | `magnetic_calculation` | Magnetic properties (Fe, Ni, Co) |
                | `troubleshoot` | Diagnose calculation problems |
                | `compare_structures` | Compare multiple structures |
                
                ---
                
                ### 🧲 Auto-Detected Magnetic Elements
                
                The following elements automatically enable `spin_polarized=True`:
                
                `Fe` `Co` `Ni` `Mn` `Cr` `V` `Gd` `Eu` `Tb` `Dy` `Ho` `Er`
                
                ---
                
                ### 📊 Smart Defaults
                
                | Parameter | Auto-Detection Method |
                |-----------|----------------------|
                | `ecutwfc` | From pseudopotential hints (30-80 Ry typical) |
                | `ecutrho` | 4× ecutwfc (NC pseudos) |
                | `kpoints` | Cell-size based: smaller cell → denser grid |
                | `spin_polarized` | True for magnetic elements |
                | `smearing` | "cold" (Marzari-Vanderbilt) - works for metals & semiconductors |
                """)
            
            with gr.Tab("⚙️ Setup"):
                config_output = gr.Markdown(value=show_mcp_config())
            
            with gr.Tab("📤 Example Outputs"):
                gr.Markdown("""
                ## Example Tool Return Values
                
                ### `qe_run_scf` for Silicon
                ```json
                {
                    "success": true,
                    "converged": true,
                    "total_energy_eV": -214.4906,
                    "total_energy_Ry": -15.7726,
                    "fermi_energy_eV": 6.2975,
                    "n_iterations": 4,
                    "forces_eV_per_angstrom": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                    "stress_kbar": null,
                    "total_magnetization": null,
                    "walltime_seconds": 12.5,
                    "output_dir": "/qe_calculations/scf_abc123",
                    "parameters_used": {
                        "spin_polarized": false,
                        "smearing": "cold",
                        "degauss": 0.02
                    }
                }
                ```
                
                ### `qe_workflow_bandstructure` for GaAs
                ```json
                {
                    "success": true,
                    "workflow_id": "bands_xyz789",
                    "band_gap_eV": 0.48,
                    "is_metal": false,
                    "is_direct_gap": true,
                    "vbm_eV": -0.24,
                    "cbm_eV": 0.24,
                    "fermi_energy_eV": 5.1234,
                    "total_energy_eV": -312.8765,
                    "n_bands": 24,
                    "n_kpoints": 100,
                    "high_symmetry_points": {
                        "Γ": [0.0, 0.0, 0.0],
                        "X": [0.5, 0.0, 0.5],
                        "W": [0.5, 0.25, 0.75],
                        "L": [0.5, 0.5, 0.5]
                    }
                }
                ```
                
                ### `qe_workflow_dos` for Iron (magnetic)
                ```json
                {
                    "success": true,
                    "workflow_id": "dos_mag456",
                    "fermi_energy_eV": 17.8432,
                    "dos_fermi_eV": 17.8432,
                    "energies_eV": [-10.0, -9.99, "...", 10.0],
                    "dos": [0.12, 0.15, "...", 0.08],
                    "integrated_dos": [0.0, 0.01, "...", 8.0],
                    "energy_range_eV": [-10.0, 10.0],
                    "n_points": 2001,
                    "total_energy_eV": -3220.5287
                }
                ```
                
                ### `qe_load_structure` for Cu
                ```json
                {
                    "success": true,
                    "formula": "Cu",
                    "n_atoms": 1,
                    "symbols": ["Cu"],
                    "cell": [
                        [0.0, 1.805, 1.805],
                        [1.805, 0.0, 1.805],
                        [1.805, 1.805, 0.0]
                    ],
                    "volume_angstrom3": 11.76,
                    "positions": [[0.0, 0.0, 0.0]],
                    "pbc": [true, true, true]
                }
                ```
                
                ### `qe_validate_structure` for Si
                ```json
                {
                    "valid": true,
                    "formula": "Si2",
                    "n_atoms": 2,
                    "volume_angstrom3": 40.05,
                    "errors": [],
                    "warnings": [],
                    "recommendations": {
                        "ecutwfc_Ry": 40.0,
                        "ecutrho_Ry": 160.0,
                        "kpoints": [7, 7, 7]
                    }
                }
                ```
                """)
            
            with gr.Tab("🧪 Elements"):
                elements_output = gr.Markdown(value=list_elements())
            
            with gr.Tab("🖥️ Status"):
                status_output = gr.Markdown(value=get_server_status())
                refresh_btn = gr.Button("🔄 Refresh Status")
                refresh_btn.click(get_server_status, outputs=[status_output])
        
        gr.Markdown("""
        ---
        
        ### 🏗️ Architecture
        
        ```
        User (natural language) → LLM (Claude/GPT) → MCP Protocol → QE-MCP Server → Docker (QE v6.7) → Results
        ```
        
        ### 📦 MCP Server Components
        
        ```
        qe_mcp/
        ├── server.py              # MCP server entry point
        ├── config.py              # Configuration management
        ├── tools/
        │   ├── calculations.py    # SCF, relax, vc-relax tools
        │   ├── postprocessing.py  # bands.x, dos.x, projwfc.x
        │   ├── workflows.py       # Multi-step workflows
        │   ├── utilities.py       # Structure loading, k-paths
        │   └── data_access.py     # Read output files
        ├── core/
        │   ├── structures.py      # ASE structure handling
        │   ├── pseudopotentials.py# SG15 library management
        │   ├── input_generator.py # QE input file generation
        │   ├── runner.py          # Docker/local execution
        │   └── parser.py          # Output parsing
        ├── resources/             # Documentation resources
        └── prompts/               # Guided workflow prompts
        ```
        
        ### 🛠️ Tech Stack
        - **Quantum ESPRESSO v6.7MaX** - DFT engine
        - **MCP SDK** (mcp>=1.0.0) - Model Context Protocol  
        - **ASE 3.26** - Atomic Simulation Environment
        - **Docker** - Containerized QE
        - **SG15 ONCV** - 69 element pseudopotentials
        
        ### 🔬 Capabilities
        
        | Calculation Type | Description |
        |-----------------|-------------|
        | **SCF** | Ground state energy, charge density |
        | **Relax** | Atomic position optimization |
        | **VC-Relax** | Full cell optimization |
        | **Bands** | Electronic band structure |
        | **DOS** | Density of states |
        | **PDOS** | Orbital-projected DOS |
        
        ---
        
        *Built for [MCP's 1st Birthday Hackathon](https://huggingface.co/MCP-1st-Birthday) 🎂 by [@frimpsjoe](https://huggingface.co/frimpsjoe)*
        """)
    
    return demo

# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    # Create and launch Gradio app
    demo = create_gradio_app()
    demo.launch(server_name="0.0.0.0", server_port=7860)
