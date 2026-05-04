# Quantum ESPRESSO MCP Server

An MCP (Model Context Protocol) server for running Quantum ESPRESSO DFT calculations. This allows any MCP-compatible LLM client to perform first-principles materials simulations.

## Features

- **Core Calculations**: SCF, structure relaxation (fixed/variable cell)
- **Band Structure**: Complete workflow with automatic k-path generation
- **Density of States**: Total DOS and projected DOS (PDOS)
- **Docker Integration**: Run QE via Docker for easy setup
- **SG15 Pseudopotentials**: Uses optimized norm-conserving pseudopotentials

## Installation

### Prerequisites

1. **Docker** with the QE image:
   ```bash
   docker build -t qe-local .
   ```

2. **uv** (Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

### Setup

```bash
# Clone and enter directory
cd qe-mcp

# Download pseudopotentials
python scripts/download_pseudos.py

# Install dependencies
uv sync

# Test the server
uv run qe-mcp
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `QE_USE_DOCKER` | Use Docker runner | `true` |
| `QE_DOCKER_IMAGE` | Docker image name | `qe-local` |
| `QE_NPROCS` | Number of MPI processes | `1` |
| `QE_PSEUDO_DIR` | Pseudopotential directory | `./pseudopotentials/sg15_oncv` |
| `QE_WORKDIR` | Calculation working directory | `./qe_calculations` |

### Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "quantum-espresso": {
      "command": "uv",
      "args": ["--directory", "/path/to/qe-mcp", "run", "qe-mcp"],
      "env": {
        "QE_USE_DOCKER": "true",
        "QE_DOCKER_IMAGE": "qe-local",
        "QE_NPROCS": "4"
      }
    }
  }
}
```

## Available Tools

### Core Calculations

| Tool | Description |
|------|-------------|
| `qe_run_scf` | Self-consistent field calculation |
| `qe_run_relax` | Atomic position relaxation |
| `qe_run_vc_relax` | Variable-cell relaxation |

### Workflows

| Tool | Description |
|------|-------------|
| `qe_workflow_bandstructure` | Complete band structure calculation |
| `qe_workflow_dos` | Complete DOS calculation |
| `qe_workflow_relax_and_scf` | Relaxation + accurate SCF |

### Utilities

| Tool | Description |
|------|-------------|
| `qe_load_structure` | Load and inspect structure |
| `qe_validate_structure` | Validate structure and suggest parameters |
| `qe_list_pseudopotentials` | List available pseudopotentials |
| `qe_suggest_kpoints` | Suggest k-point grid |
| `qe_status` | Server status and configuration |

## Example Usage

Once connected to an MCP client (like Claude Desktop):

```
Calculate the band structure of silicon
```

The LLM will call `qe_workflow_bandstructure` with `structure="Si"` and return the band gap, VBM, CBM, and other results.

## License

MIT
