"""
Prompt templates for QE-MCP.

Pre-built prompts for common DFT calculation workflows.
"""

from typing import Any

PROMPTS = {
    "band_structure": {
        "name": "Band Structure Calculation",
        "description": "Calculate electronic band structure for a material",
        "arguments": [
            {
                "name": "material",
                "description": "Chemical formula or structure description (e.g., 'Si', 'GaAs', 'Fe2O3')",
                "required": True,
            },
            {
                "name": "accuracy",
                "description": "Calculation accuracy: 'low', 'medium', or 'high'",
                "required": False,
            },
        ],
        "template": """You are a computational materials scientist assistant. The user wants to calculate the band structure of {material}.

Please perform the following steps:

1. First, use `list_pseudopotentials` to verify pseudopotentials are available for all elements in {material}.

2. Use `workflow_bandstructure` to calculate the band structure with these parameters:
   - structure: "{material}"
   - ecutwfc: {ecutwfc} (based on accuracy level)
   - npoints_band: {npoints} (k-points along path)

3. Analyze the results and report:
   - Total energy
   - Fermi energy
   - Band gap (if semiconductor/insulator)
   - Whether the material is metallic or not
   - If semiconductor: direct or indirect gap
   - High-symmetry k-points used

4. Provide a brief interpretation of the electronic structure.

Accuracy settings:
- low: ecutwfc=40, npoints=50
- medium: ecutwfc=60, npoints=100
- high: ecutwfc=80, npoints=150
""",
    },
    "dos_calculation": {
        "name": "Density of States Calculation",
        "description": "Calculate total and projected density of states",
        "arguments": [
            {
                "name": "material",
                "description": "Chemical formula or structure (e.g., 'Cu', 'Fe', 'TiO2')",
                "required": True,
            },
            {
                "name": "spin_polarized",
                "description": "Whether to include spin polarization (for magnetic materials)",
                "required": False,
            },
        ],
        "template": """You are a computational materials scientist assistant. The user wants to calculate the density of states (DOS) for {material}.

Please perform the following steps:

1. First, check if {material} contains magnetic elements (Fe, Co, Ni, Mn, Cr, etc.). If so, set spin_polarized=True.

2. Use `workflow_dos` to calculate the DOS:
   - structure: "{material}"
   - spin_polarized: {spin_polarized}
   - ecutwfc: 60
   - kpoints_nscf: [12, 12, 12] (dense grid for DOS)

3. Analyze and report:
   - Total energy and Fermi energy
   - Energy range of the DOS
   - Key features (peaks, gaps, d-band position if applicable)
   - For magnetic materials: spin-up vs spin-down distribution

4. Provide interpretation relevant to the material type:
   - For metals: position of d-band center (important for catalysis)
   - For semiconductors: band edges and gap
   - For magnetic materials: exchange splitting
""",
    },
    "geometry_optimization": {
        "name": "Geometry Optimization",
        "description": "Optimize atomic positions and/or cell parameters",
        "arguments": [
            {
                "name": "structure",
                "description": "Structure file path or formula (e.g., 'H2O', 'POSCAR', 'structure.cif')",
                "required": True,
            },
            {
                "name": "optimize_cell",
                "description": "Whether to optimize unit cell (True for crystals, False for molecules)",
                "required": False,
            },
        ],
        "template": """You are a computational materials scientist assistant. The user wants to optimize the geometry of {structure}.

Please perform the following steps:

1. First, use `load_structure_tool` to load and examine the structure.

2. Determine the appropriate calculation type:
   - If optimize_cell=True or it's a bulk crystal: use `run_vc_relax`
   - If optimize_cell=False or it's a molecule/slab: use `run_relax`

3. Run the optimization with appropriate parameters:
   - ecutwfc: 60 (adjust based on elements)
   - For molecules: ensure sufficient vacuum (at least 10 Å)
   - For slabs: fix bottom layers if needed

4. Report the results:
   - Initial vs final energy
   - Number of optimization steps
   - Final forces (max force on atoms)
   - Cell changes (for vc-relax)
   - Significant structural changes

5. If forces are not well converged, suggest:
   - Running additional steps
   - Adjusting convergence thresholds
   - Checking for potential issues
""",
    },
    "convergence_test": {
        "name": "Convergence Testing",
        "description": "Test convergence of calculation parameters",
        "arguments": [
            {
                "name": "material",
                "description": "Material to test (e.g., 'Si', 'Cu')",
                "required": True,
            },
            {
                "name": "parameter",
                "description": "Parameter to test: 'ecutwfc', 'kpoints', or 'both'",
                "required": False,
            },
        ],
        "template": """You are a computational materials scientist assistant. The user wants to test convergence for {material}.

Please perform systematic convergence tests:

## Ecutwfc Convergence (if parameter includes 'ecutwfc' or 'both')

Run SCF calculations with increasing ecutwfc:
1. ecutwfc = 30 Ry
2. ecutwfc = 40 Ry
3. ecutwfc = 50 Ry
4. ecutwfc = 60 Ry
5. ecutwfc = 70 Ry
6. ecutwfc = 80 Ry

For each, use `run_scf` and record total energy.

## K-points Convergence (if parameter includes 'kpoints' or 'both')

Run SCF calculations with increasing k-grid density:
1. kpoints = [4, 4, 4]
2. kpoints = [6, 6, 6]
3. kpoints = [8, 8, 8]
4. kpoints = [10, 10, 10]
5. kpoints = [12, 12, 12]

Use a well-converged ecutwfc for these tests.

## Analysis

Create a convergence table showing:
- Parameter value
- Total energy (eV)
- Energy difference from previous step (meV)
- Energy difference from most converged value (meV)

Recommend the converged values where:
- Energy change < 1 meV/atom between successive values
- Good balance between accuracy and computational cost
""",
    },
    "surface_calculation": {
        "name": "Surface Energy Calculation",
        "description": "Calculate surface energy and work function",
        "arguments": [
            {
                "name": "material",
                "description": "Bulk material (e.g., 'Cu', 'Pt', 'Au')",
                "required": True,
            },
            {
                "name": "surface",
                "description": "Miller indices (e.g., '111', '100', '110')",
                "required": True,
            },
            {
                "name": "layers",
                "description": "Number of atomic layers (default: 6)",
                "required": False,
            },
        ],
        "template": """You are a computational materials scientist assistant. The user wants to calculate surface properties for {material}({surface}).

Please perform the following calculations:

## 1. Bulk Reference
First, calculate the bulk energy per atom:
- Use `run_scf` for bulk {material}
- Record E_bulk and number of atoms

## 2. Slab Calculation
Build and calculate the slab:
- Use ASE to build {material}({surface}) slab with {layers} layers
- Add 15 Å vacuum
- Use `run_relax` to optimize the surface (fix bottom 2 layers)
- Record E_slab and number of atoms

## 3. Surface Energy
Calculate: γ = (E_slab - n × E_bulk) / (2 × A)

Where:
- E_slab = total slab energy
- n = number of atoms in slab  
- E_bulk = bulk energy per atom
- A = surface area
- Factor of 2 for two surfaces

## 4. Work Function (optional)
From the electrostatic potential:
- Φ = V_vacuum - E_Fermi

## Report
- Bulk energy per atom
- Slab total energy
- Surface area
- Surface energy (J/m² or eV/Å²)
- Comparison with experimental values if available
""",
    },
    "magnetic_calculation": {
        "name": "Magnetic Properties Calculation",
        "description": "Calculate magnetic properties of a material",
        "arguments": [
            {
                "name": "material",
                "description": "Magnetic material (e.g., 'Fe', 'Ni', 'Fe3O4')",
                "required": True,
            },
            {
                "name": "configuration",
                "description": "Magnetic configuration: 'ferromagnetic', 'antiferromagnetic', or 'both'",
                "required": False,
            },
        ],
        "template": """You are a computational materials scientist assistant. The user wants to calculate magnetic properties of {material}.

Please perform the following:

## 1. Ferromagnetic Calculation
- Use `run_scf` with spin_polarized=True
- Initial magnetization: all atoms spin-up
- Record total magnetization and total energy

## 2. Antiferromagnetic Calculation (if applicable)
For materials with multiple magnetic atoms:
- Set alternating spin directions
- This may require manual structure setup
- Record total magnetization and total energy

## 3. Analysis
Report:
- Total magnetic moment (Bohr magnetons)
- Magnetic moment per magnetic atom
- Energy difference between FM and AFM (if both calculated)
- Exchange energy estimate

## 4. Spin-polarized DOS
Use `workflow_dos` with spin_polarized=True to show:
- Spin-up vs spin-down DOS
- Exchange splitting
- Magnetic orbital contributions
""",
    },
    "troubleshoot": {
        "name": "Troubleshoot Calculation",
        "description": "Help diagnose and fix common DFT calculation issues",
        "arguments": [
            {
                "name": "problem",
                "description": "Description of the problem (e.g., 'SCF not converging', 'negative frequencies')",
                "required": True,
            },
            {
                "name": "material",
                "description": "Material being calculated",
                "required": False,
            },
        ],
        "template": """You are a computational materials scientist assistant. The user is experiencing: {problem}

Please help diagnose and resolve this issue.

## Common Problems and Solutions

### SCF Not Converging
1. **Reduce mixing_beta**: Try 0.3 instead of 0.7
2. **Increase mixing_ndim**: Try 12 or 16
3. **Use local-TF mixing**: For metals with localized d/f electrons
4. **Add smearing**: For metals, use degauss=0.02
5. **Check structure**: Atoms too close? Vacuum too small?

### Geometry Not Converging
1. **Increase ecutwfc**: Forces need higher cutoff than energies
2. **Reduce forc_conv_thr**: Try 1e-3 instead of 1e-4
3. **Check k-points**: Need Gamma-centered for some structures
4. **Reduce trust_radius**: For difficult optimizations

### Memory Issues
1. **Reduce ecutwfc**: If possible without losing accuracy
2. **Fewer k-points**: Use symmetry
3. **disk_io='low'**: Store less on disk

### Bands Calculation Fails
1. **Check prefix**: Must match SCF calculation
2. **Check outdir**: Must contain SCF data
3. **Trailing newline**: Input file needs newline at end

## Diagnostic Steps
1. Check the output file for specific error messages
2. Verify pseudopotentials are correct
3. Ensure structure is reasonable (no overlapping atoms)
4. Check computational resources (memory, disk space)

Based on your specific problem "{problem}", I recommend:
[Analysis and recommendations based on the problem description]
""",
    },
    "compare_structures": {
        "name": "Compare Structures",
        "description": "Compare energies and properties of different structures",
        "arguments": [
            {
                "name": "structures",
                "description": "Comma-separated list of structures to compare",
                "required": True,
            },
        ],
        "template": """You are a computational materials scientist assistant. The user wants to compare the following structures: {structures}

Please perform SCF calculations on each structure and compare:

## Calculations
For each structure:
1. Use `run_scf` with consistent parameters:
   - ecutwfc: 60
   - kpoints: appropriate for each structure type

## Comparison Table
Create a table with:
| Structure | Total Energy (eV) | Energy/atom (eV) | Volume (Å³) | Density |

## Analysis
1. **Most stable structure**: Lowest energy per atom
2. **Energy differences**: Relative to most stable
3. **Structural differences**: Bond lengths, angles, coordination
4. **Property predictions**: Which structure is expected for given conditions

## Phase Stability
If comparing polymorphs:
- Which is ground state?
- Approximate transition pressure/temperature
- Kinetic stability considerations
""",
    },
}


def list_prompts() -> list[dict]:
    """List all available prompt templates."""
    return [
        {
            "name": name,
            "description": info["description"],
            "arguments": info.get("arguments", []),
        }
        for name, info in PROMPTS.items()
    ]


def get_prompt(name: str, arguments: dict[str, Any] | None = None) -> dict | None:
    """
    Get a prompt template, optionally filled with arguments.
    
    Args:
        name: Name of the prompt template
        arguments: Dictionary of argument values to fill in
        
    Returns:
        Dictionary with prompt messages, or None if not found
    """
    if name not in PROMPTS:
        return None
    
    prompt_info = PROMPTS[name]
    template = prompt_info["template"]
    
    # Fill in default values for missing arguments
    args = arguments or {}
    
    # Set defaults based on prompt type
    if name == "band_structure":
        accuracy = args.get("accuracy", "medium")
        if accuracy == "low":
            args["ecutwfc"] = 40
            args["npoints"] = 50
        elif accuracy == "high":
            args["ecutwfc"] = 80
            args["npoints"] = 150
        else:  # medium
            args["ecutwfc"] = 60
            args["npoints"] = 100
    
    elif name == "dos_calculation":
        args.setdefault("spin_polarized", False)
    
    elif name == "geometry_optimization":
        args.setdefault("optimize_cell", False)
    
    elif name == "convergence_test":
        args.setdefault("parameter", "both")
    
    elif name == "surface_calculation":
        args.setdefault("layers", 6)
    
    elif name == "magnetic_calculation":
        args.setdefault("configuration", "ferromagnetic")
    
    # Format the template with arguments
    try:
        filled_template = template.format(**args)
    except KeyError as e:
        # Return template with placeholders if arguments missing
        filled_template = template
    
    return {
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": filled_template,
                },
            }
        ]
    }
