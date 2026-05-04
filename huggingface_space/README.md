---
title: Quantum ESPRESSO MCP Server
emoji: ⚛️
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.8.0"
app_file: app.py
pinned: false
license: mit
tags:
  - mcp
  - quantum-espresso
  - dft
  - materials-science
  - building-mcp-track-enterprise
  - building-mcp-track-consumer
---

# ⚛️ Quantum ESPRESSO MCP Server

> **Run DFT calculations with natural language!** An MCP server that enables LLMs to perform first-principles quantum mechanical simulations.

[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Quantum ESPRESSO](https://img.shields.io/badge/QE-v6.7-green)](https://www.quantum-espresso.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What This Does

This MCP server allows AI agents (Claude, GPT, etc.) to:
- **Calculate total energies** of materials (Si, Fe, Cu, GaAs...)
- **Compute band structures** and find band gaps
- **Run density of states** calculations
- **Optimize crystal structures** (relax atoms and cells)
- **Handle magnetic materials** automatically (Fe, Co, Ni...)

**Just say:** *"Calculate the band structure of silicon"* - and the AI does the rest!

## 🔧 16 MCP Tools Available

### Core Calculations
| Tool | Description |
|------|-------------|
| `qe_run_scf` | Self-consistent field calculation (total energy) |
| `qe_run_relax` | Optimize atomic positions |
| `qe_run_vc_relax` | Variable-cell relaxation |

### Workflows
| Tool | Description |
|------|-------------|
| `qe_workflow_bandstructure` | Complete band structure workflow |
| `qe_workflow_dos` | Density of states calculation |
| `qe_workflow_relax_and_scf` | Relax then accurate SCF |

### Utilities
| Tool | Description |
|------|-------------|
| `qe_load_structure` | Load structures (files, formulas, 2D materials, MP) |
| `qe_search_materials_project` | Search Materials Project database |
| `qe_get_mp_structure` | Get structure by Materials Project ID |
| `qe_get_kpath` | Get k-path for band structure |
| `qe_suggest_kpoints` | Auto-suggest k-point grid |
| `qe_list_pseudopotentials` | List 69 available elements |
| `qe_validate_structure` | Check structure for issues |
| `qe_status` | Server status |

### Data Access
| Tool | Description |
|------|-------------|
| `qe_read_bands` | Read band structure data |
| `qe_read_dos` | Read DOS data |
| `qe_read_pdos` | Read projected DOS |
| `qe_list_files` | List output files |

## ✨ Key Features

### 🧠 Smart Auto-Detection
- **Only `structure` is required** - everything else is auto-detected!
- K-points automatically chosen based on cell size
- Cutoffs from SG15 pseudopotentials
- Spin polarization auto-enabled for Fe, Co, Ni, Mn, Cr, V

### � Flexible Structure Input

**Files:** `.cif`, `.vasp`, `.poscar`, `.xyz`, `.extxyz`, `.pdb`, `.xsf`

**Built-in Formulas:**
- **Bulk:** Si, Cu, Fe, GaAs, NaCl, MgO, ZnO, GaN, and 60+ more
- **2D Materials:** graphene, hBN, MoS2, WS2, phosphorene
- **Perovskites:** SrTiO3, BaTiO3, LaMnO3, LaAlO3, etc.
- **Molecules:** H2O, CO2, CH4, C6H6, NH3, and 40+ more

**Materials Project Integration:**
```
qe_load_structure("mp-149")  # Silicon from MP database
qe_search_materials_project("Li-Fe-O")  # Search for materials
```
*Requires `MP_API_KEY` environment variable*

**Inline XYZ+Lattice:**
```
"xyz:C 0 0 0; C 1.42 0 0|lattice:2.46,0,0,0,4.26,0,0,0,15"
```

### �📚 69 Elements Supported
Full periodic table coverage with SG15 ONCV pseudopotentials:
> Ag, Al, Ar, As, Au, B, Ba, Be, Bi, Br, C, Ca, Cd, Cl, Co, Cr, Cs, Cu, F, Fe, Ga, Ge, H, He, Hf, Hg, I, In, Ir, K, Kr, La, Li, Mg, Mn, Mo, N, Na, Nb, Ne, Ni, O, Os, P, Pb, Pd, Pt, Rb, Re, Rh, Ru, S, Sb, Sc, Se, Si, Sn, Sr, Ta, Tc, Te, Ti, Tl, V, W, Xe, Y, Zn, Zr

### 🎯 8 Prompts for Guided Workflows
- `band_structure` - Band structure calculation guide
- `dos_calculation` - DOS workflow
- `geometry_optimization` - Structure relaxation
- `convergence_test` - Parameter testing
- `surface_calculation` - Surface energy
- `magnetic_calculation` - Magnetic properties
- `troubleshoot` - Diagnose problems
- `compare_structures` - Compare materials

## 🚀 Quick Start

### Use with Claude Desktop (Local)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Then ask Claude:
- *"Calculate the total energy of silicon"*
- *"What's the band gap of GaAs?"*
- *"Run a spin-polarized calculation for iron"*

## 📊 Example Results

### Silicon SCF
```
Total Energy: -214.49 eV
Fermi Energy: 6.30 eV
Converged: 4 iterations
```

### Iron (Magnetic)
```
Total Energy: -3220.53 eV
Magnetization: 7.63 μB
Spin-polarized: Auto-enabled
```

### GaAs Band Structure
```
Band Gap: 0.56 eV (indirect)
VBM → CBM: Γ → X
```

## 🏗️ Architecture

```
User (natural language)
    ↓
LLM (Claude/GPT)
    ↓
MCP Protocol
    ↓
QE-MCP Server (Python)
    ↓
Docker Container (Quantum ESPRESSO v6.7)
    ↓
DFT Calculation Results
    ↓
Structured Output (JSON)
```

## 📦 Package Structure

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

## 🛠️ Tech Stack

- **Quantum ESPRESSO v6.7MaX** - DFT engine
- **MCP SDK** (mcp>=1.0.0) - Model Context Protocol
- **ASE 3.26** - Atomic Simulation Environment
- **Docker** - Containerized QE
- **SG15 ONCV** - Pseudopotentials (69 elements)

## 👤 Team

- **Joseph Frimpong** - [@frimpsjoe](https://huggingface.co/frimpsjoe)

## 📜 License

MIT License

---

*Built for [MCP's 1st Birthday Hackathon](https://huggingface.co/MCP-1st-Birthday) 🎂*
