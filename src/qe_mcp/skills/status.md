---
name: Job Status Skill
description: Job dashboard — check server health, Docker/Globus runner status, and the status of one or more QE jobs.
arguments:
  - name: job_ids
    description: Optional comma-separated job IDs to check (e.g., 'scf_abc123, bands_def456'). Leave blank for server health only.
    required: false
---
You are displaying a QE MCP status dashboard.

## Step 1 — Server health
Call `qe_status()` and report:
- Server version and runner type (Docker / Globus)
- Docker container reachability (for Docker runner)
- Pseudopotential directory and element count
- Working directory path

## Step 2 — Job statuses (if job_ids provided)
If `{job_ids}` is not empty, split by commas and call `qe_get_job_status(job_id=<id>)` for each.

Format the results as a dashboard table:

| Job ID | Type | Material | Status | Notes |
|--------|------|----------|--------|-------|
| scf_abc | SCF | Si | ✓ completed | E = −215.3 eV |
| bands_def | Bands | GaAs | ⟳ running | Step 2/3: NSCF |
| relax_ghi | Relax | Fe | ✗ failed | SCF not converged |

Status icons:
- `✓ completed` — job finished successfully
- `⟳ running` / `submitted` — job in progress
- `✗ failed` — job encountered an error

## Step 3 — Next steps for failed jobs
For each failed job, suggest a specific remedy based on the job type:
- SCF failure → suggest `skill_troubleshoot` with the error description
- Bands failure → check that prefix/outdir match the SCF job
- Relax failure → suggest restarting from last geometry with tighter thresholds

## Step 4 — Summary line
End with a one-line summary: "X of Y jobs completed, Z running, W failed."
