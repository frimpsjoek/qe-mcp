---
name: Troubleshoot Skill
description: Diagnose and fix common QE calculation failures — SCF convergence, geometry stalls, memory errors, bands mismatches, and pseudopotential issues.
arguments:
  - name: problem
    description: Description of the problem (e.g., 'SCF not converging for NiO', 'bands calculation failed')
    required: true
  - name: material
    description: Material being calculated (optional but helps diagnosis)
    required: false
---
You are diagnosing and fixing a QE calculation problem.

**Problem reported:** {problem}  
**Material:** {material}

## Step 1 — Classify the problem
Read `qe://llm/decision-guide` (error handling section) and match the problem to one of these categories:

| Category | Keywords |
|----------|---------|
| SCF convergence | "not converging", "too many iterations", "charge density oscillating" |
| Geometry stall | "not converging" in relax, "maximum number of steps", "negative eigenvalues" |
| Memory / disk | "out of memory", "no space left", "segfault" |
| Bands mismatch | "wrong number of bands", "cannot read save", "prefix mismatch" |
| Pseudopotential | "PP not found", "element not supported", "incompatible PP" |
| Negative frequencies | "imaginary frequency", "phonon" |

## Step 2 — Read the output (if a job can be identified)
If a job ID or directory is mentioned in `{problem}`, call `qe_list_files` to locate the `.out` file, then read the last ~100 lines for the specific QE error message. Quote the exact error line in your diagnosis.

## Step 3 — Apply targeted fix

### SCF Not Converging
1. **Reduce `mixing_beta`** to 0.3 (default 0.7 is too aggressive for strongly correlated systems)
2. **Increase `mixing_ndim`** to 16 (more history for Pulay mixing)
3. **For transition metal oxides**: use `mixing_mode='local-TF'` for better charge localisation
4. **Add or increase smearing**: try `degauss=0.03` for metals
5. **Check for magnetic elements**: if Fe/Co/Ni/Mn present and `spin_polarized=False`, enable it
6. **Reduce initial step**: try `electron_maxstep=200`

### Geometry Not Converging
1. **Increase `ecutwfc`**: forces require higher cutoff than energies (try +20 Ry)
2. **Relax `forc_conv_thr`**: loosen to `1.0e-3` for an initial optimisation
3. **Restart from last geometry**: use the output structure as the new input

### Memory / Disk Issues
1. **Reduce `ecutwfc`** if possible
2. **Use `disk_io='low'`** to minimise wavefunction writes
3. **Reduce k-points** temporarily
4. **Check available disk space** in the working directory

### Bands Calculation Failing
1. **Verify `prefix` matches the SCF calculation exactly** (case-sensitive)
2. **Verify `outdir` points to the correct save directory** containing `<prefix>.save/`
3. **Re-run SCF** if the save directory is missing or corrupted

### Pseudopotential Issues
1. Call `qe_list_pseudopotentials` to check which elements are supported
2. Verify the element symbol is spelled correctly
3. If an element is missing from the SG15 ONCV library, suggest an alternative PP source

## Step 4 — Propose a corrected call
Based on the diagnosis, provide the specific corrected tool call with the recommended parameter changes, ready for the user to execute.
