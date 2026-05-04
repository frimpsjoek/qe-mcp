---
name: Plot Skill
description: Generate publication-quality matplotlib scripts from completed QE calculations (bands, DOS, PDOS).
arguments:
  - name: job_id
    description: Job ID or working directory path from a completed calculation
    required: true
---
You are generating publication-quality plots for job **{job_id}**.

## ABSOLUTE RULES — read before doing anything else

1. **Output Python + matplotlib ONLY.** Never use JavaScript, Plotly, Bokeh, D3, Vega, or any interactive/browser-based plotting library. The user explicitly does not want interactive plots.
2. **Never render or display a plot inline.** Produce a `.py` script that saves a static PDF file. Do not call `plt.show()`.
3. **Never fabricate data.** Every value in the script must come from the tool calls in Steps 1–2.

## Step 1 — Discover available data
Call `qe_list_files(job_id="{job_id}")` and identify which output files exist:
- `*.gnu` — band structure data (from bands.x)
- `*.dat` / `*dos.dat` — total DOS data (from dos.x)
- `*.pdos_atm*` / `*.pdos_tot` — projected DOS (from projwfc.x)

Report what plot types are possible based on available files.

## Step 2 — Read data
- If bands file found: call `qe_read_bands(job_id="{job_id}")`
- If DOS file found: call `qe_read_dos(job_id="{job_id}")`
- If PDOS files found: call `qe_read_pdos(job_id="{job_id}")`

**NEVER fabricate or estimate data values. Only plot data from these tool calls.**

## Step 3 — Generate plotting script
Read `qe://llm/plotting` for the full style guide. Apply all conventions strictly:

**Universal settings:**
```python
import matplotlib
matplotlib.rcParams.update({
    'font.family': 'Arial',
    'font.size': 8,
    'axes.linewidth': 0.5,
    'lines.linewidth': 0.6,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'figure.dpi': 300,
})
```

**Band structure (if available):**
- Figure size: 3.5 × 4 in
- Shift all bands by −E_Fermi so Fermi level is at 0 eV
- Show E_Fermi as grey dashed line at y=0
- Label high-symmetry points on x-axis
- Energy window: −4 to +4 eV (adjust if gap is large)
- Remove top and right spines

**DOS (if available):**
- Energy on x-axis, DOS on y-axis
- Apply 0.03 eV Gaussian broadening to smooth the DOS curve
- Shift energy axis so E_Fermi = 0 eV
- Vertical dashed line at x=0 (E_Fermi)
- Energy window: −5 to +5 eV
- For spin-polarized: spin-up positive, spin-down as negative mirror

**PDOS (if available):**
- Plot s, p, d (and f if present) contributions with distinct muted colours: #2c3e50, #3498db, #e74c3c, #2ecc71
- Include total DOS as a filled grey area behind orbital contributions
- Legend outside top-right

**Combined bands + DOS panel (if both available):**
- Side-by-side subplots sharing the y-axis (energy)
- Band structure on left, DOS on right
- Single shared y-axis label "Energy (eV)"

## Step 4 — Output
Provide a complete, runnable Python script with:
- All actual file paths from Step 2 hardcoded (no placeholders)
- `plt.savefig("figure.pdf", bbox_inches="tight")` at the end
- A comment at the top with the job_id and material name
