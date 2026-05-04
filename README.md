# Quantum ESPRESSO MCP Server

An MCP (Model Context Protocol) server for running Quantum ESPRESSO DFT calculations. This allows any MCP-compatible LLM client to perform first-principles materials simulations.

## Features

- **Core Calculations**: SCF, structure relaxation (fixed/variable cell)
- **Band Structure**: Complete workflow with automatic k-path generation
- **Density of States**: Total DOS and projected DOS (PDOS)
- **Docker Integration**: Run QE via Docker for easy setup
- **Polaris HPC Integration**: Submit QE jobs to ALCF Polaris through Globus Compute
- **SG15 Pseudopotentials**: Uses optimized norm-conserving pseudopotentials
- **Async Job Tracking**: Long-running Globus jobs return job IDs and can be checked later

## Installation

### Prerequisites

1. **uv** (Python package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Docker** for local runs, or **Globus Compute** for Polaris runs.

   For local Docker mode:
   ```bash
   docker build -t qe-local .
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

QE-MCP supports two execution modes:

- `docker`: run Quantum ESPRESSO locally inside a Docker image.
- `globus`: submit Quantum ESPRESSO calculations to Polaris with Globus Compute.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `QE_RUNNER` | Runner backend: `docker`, `local`, `globus`, or `polaris` | `docker` if Docker is enabled |
| `QE_USE_DOCKER` | Use Docker runner | `false` |
| `QE_DOCKER_IMAGE` | Docker image name | `qe-local` |
| `QE_NPROCS` | Number of MPI processes | `1` |
| `QE_PSEUDO_DIR` | Pseudopotential directory | `./pseudopotentials/sg15_oncv` |
| `QE_WORKDIR` | Calculation working directory | `./qe_calculations` |
| `QE_GLOBUS_ENDPOINT` | Globus Compute endpoint UUID for Polaris | required for `globus` |
| `QE_GLOBUS_FUNCTION` | Registered Globus Compute function UUID | auto-registered if unset |
| `QE_POLARIS_SCRATCH` | Persistent calculation directory on Polaris | `~/.qe_mcp_scratch` |
| `QE_POLARIS_PSEUDO` | Optional pre-staged SG15 directory on Polaris | unset |

## Running on Polaris with Globus Compute

Polaris mode uses Globus Compute as the execution layer. The MCP server runs on your machine, prepares QE input files, submits a self-contained worker function to the Polaris Globus Compute endpoint, and keeps large wavefunction files on Polaris. Only small text outputs needed for parsing and plotting are returned locally.

### 1. Install HPC extras

```bash
uv sync --extra hpc
```

If you are not using `uv`, install the package with the `hpc` extra in your Python environment.

### 2. Create or start a Polaris Globus Compute endpoint

On Polaris, create an endpoint using the provided config as a starting point:

```bash
globus-compute-endpoint configure qe-polaris-1
cp polaris-qespresso/qe_polaris_config ~/.globus_compute/qe-polaris-1/config.yaml
globus-compute-endpoint start qe-polaris-1
globus-compute-endpoint list
```

Copy the endpoint UUID from `globus-compute-endpoint list`; that value becomes `QE_GLOBUS_ENDPOINT`.

The included config requests the Polaris `debug` queue and loads the Quantum ESPRESSO 7.5 module path used by the worker. Adjust the PBS account, queue, walltime, or module setup in `polaris-qespresso/qe_polaris_config` for your allocation.

### 3. Register the QE worker function

From your local machine:

```bash
uv run python polaris-qespresso/polaris_worker.py
```

Paste your Polaris endpoint UUID when prompted. The script prints the environment variables to add to your MCP client:

```json
{
  "QE_RUNNER": "globus",
  "QE_GLOBUS_ENDPOINT": "<your-polaris-compute-endpoint-uuid>",
  "QE_GLOBUS_FUNCTION": "<registered-worker-function-uuid>"
}
```

The main server can also auto-register the worker if `QE_GLOBUS_FUNCTION` is not set, but explicit registration makes MCP client configuration easier to inspect.

### 4. Stage pseudopotentials on Polaris, optional but recommended

By default, required pseudopotential files are sent in each Globus Compute payload. For repeated production runs, stage the SG15 library once on Polaris and point QE-MCP at it:

```bash
uv run python scripts/stage_pseudos.py
```

Then add the printed value to your MCP client env block:

```json
{
  "QE_POLARIS_PSEUDO": "/home/<you>/sg15_oncv"
}
```

When `QE_POLARIS_PSEUDO` is set, jobs use the pre-staged files directly and do not resend pseudopotential contents.

### 5. Configure an MCP client for Polaris

Example Claude Desktop configuration:

```json
{
  "mcpServers": {
    "quantum-espresso": {
      "command": "uv",
      "args": ["--directory", "/path/to/qe-mcp", "run", "qe-mcp"],
      "env": {
        "QE_RUNNER": "globus",
        "QE_GLOBUS_ENDPOINT": "<your-polaris-compute-endpoint-uuid>",
        "QE_GLOBUS_FUNCTION": "<registered-worker-function-uuid>",
        "QE_POLARIS_SCRATCH": "~/.qe_mcp_scratch",
        "QE_POLARIS_PSEUDO": "/home/<you>/sg15_oncv",
        "QE_PSEUDO_DIR": "/path/to/qe-mcp/pseudopotentials/sg15_oncv",
        "QE_WORKDIR": "/path/to/qe-mcp/qe_calculations"
      }
    }
  }
}
```

Use `qe_status` from your MCP client to verify the endpoint is online. If it reports the endpoint is offline, SSH to Polaris and run:

```bash
globus-compute-endpoint start qe-polaris-1
```

### 6. Watch async jobs

Polaris calculations are asynchronous. Tools may return `{"status": "submitted", "job_id": "..."}` while the PBS/Globus task runs. You can check manually with `qe_get_job_status`, or run the watcher in another terminal:

```bash
uv run qe-watch
```

`qe-watch` polls submitted jobs in `QE_WORKDIR`, advances multi-step workflows such as SCF -> NSCF -> bands, and sends macOS notifications when jobs complete or fail.

### Polaris storage model

- Persistent calculation directories live under `QE_POLARIS_SCRATCH` on Polaris.
- SCF, NSCF, bands, DOS, and PDOS workflow steps reuse the same remote directory so wavefunction files remain available between jobs.
- Large `tmp/` data and wavefunction files are not copied back to the local machine.
- Small text outputs, such as `bands.dat.gnu`, are returned when needed for parsing and plotting.

## Running Locally with Docker

Build the local QE image:

```bash
docker build -t qe-local .
```

Configure your MCP client with Docker mode:

```json
{
  "QE_RUNNER": "docker",
  "QE_USE_DOCKER": "true",
  "QE_DOCKER_IMAGE": "qe-local",
  "QE_NPROCS": "4"
}
```

### Claude Desktop Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "quantum-espresso": {
      "command": "uv",
      "args": ["--directory", "/path/to/qe-mcp", "run", "qe-mcp"],
      "env": {
        "QE_RUNNER": "docker",
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
