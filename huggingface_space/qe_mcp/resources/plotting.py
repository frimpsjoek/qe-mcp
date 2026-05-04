"""
Plotting guide resource for LLMs.

This resource teaches LLMs how to plot QE data using matplotlib.
Attach this resource when the user asks to plot results.
"""

PLOTTING_GUIDE = """
# QE-MCP Plotting Guide - Publication Quality (Nature Style)

## CRITICAL: NEVER MAKE UP DATA

**You MUST read actual data from files. NEVER fabricate or invent data.**

1. **ALWAYS use the data access tools** to read real calculation results:
   - `qe_read_bands(output_dir)` - Read band structure data
   - `qe_read_dos(output_dir)` - Read DOS data
   - `qe_read_pdos(file_path)` - Read PDOS data
   - `qe_list_files(output_dir)` - List available files

2. **NEVER create fake arrays** - always read from actual files
3. **If a file doesn't exist**, tell the user to run the calculation first
4. **NEVER plot the same data twice** - one plot per dataset

## Publication Style Settings (Nature Quality)

```python
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d

# Nature-style settings
plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': 8,
    'axes.linewidth': 0.5,
    'axes.labelsize': 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'lines.linewidth': 0.8,
    'legend.fontsize': 7,
    'legend.frameon': False,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
})

# Broadening: 0.03 eV Gaussian
def broaden(dos, energies, sigma_eV=0.03):
    de = abs(energies[1] - energies[0])
    sigma_pts = sigma_eV / de
    return gaussian_filter1d(dos, sigma_pts)
```

## Band Structure (Publication Quality)

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': 0.5,
    'lines.linewidth': 0.6, 'figure.dpi': 300
})

data = qe_read_bands(output_dir)
k = np.array(data['k_distances'])
fermi = result['fermi_energy_eV']

fig, ax = plt.subplots(figsize=(3.5, 2.8))

for band in data['bands']:
    ax.plot(k, np.array(band) - fermi, color='#2c3e50', lw=0.6)

ax.axhline(0, color='#e74c3c', ls='--', lw=0.5, alpha=0.8)
ax.set_xlim(k[0], k[-1])
ax.set_ylim(-5, 5)
ax.set_xlabel('Wave vector')
ax.set_ylabel('E − E$_\\mathrm{F}$ (eV)')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('bands.pdf', format='pdf')
```

## DOS (Publication Quality) - Energy on X-axis

```python
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d

plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': 0.5,
    'lines.linewidth': 0.6, 'figure.dpi': 300
})

data = qe_read_dos(output_dir)
E = np.array(data['energies']) - result['fermi_energy_eV']
dos = np.array(data['dos'])

# Apply 0.03 eV Gaussian broadening
de = abs(E[1] - E[0])
sigma_pts = 0.03 / de
dos_smooth = gaussian_filter1d(dos, sigma_pts)

fig, ax = plt.subplots(figsize=(3.5, 2.5))

# Energy on x-axis, DOS on y-axis
ax.plot(E, dos_smooth, color='#2c3e50', lw=0.6)
ax.fill_between(E, 0, dos_smooth, color='#3498db', alpha=0.3)

# Fermi level
ax.axvline(0, color='#e74c3c', ls='--', lw=0.5, alpha=0.8)

ax.set_xlim(-5, 5)
ax.set_ylim(0, None)
ax.set_xlabel('E − E$_\\mathrm{F}$ (eV)')
ax.set_ylabel('DOS (arb.)')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('dos.pdf', format='pdf')
```

## PDOS (Publication Quality) - Energy on X-axis

```python
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d

plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': 0.5,
    'lines.linewidth': 0.6, 'figure.dpi': 300
})

files = qe_list_files(output_dir)
fermi = result['fermi_energy_eV']
colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6']

fig, ax = plt.subplots(figsize=(3.5, 2.5))

for i, pf in enumerate(files['pdos_files'][:4]):
    data = qe_read_pdos(pf)
    E = np.array(data['energies']) - fermi
    ldos = np.array(data['ldos'])
    
    # Apply 0.03 eV broadening
    de = abs(E[1] - E[0])
    ldos_smooth = gaussian_filter1d(ldos, 0.03 / de)
    
    ax.fill_between(E, 0, ldos_smooth, alpha=0.4, color=colors[i % 4])

ax.axvline(0, color='#e74c3c', ls='--', lw=0.5, alpha=0.8)
ax.set_xlim(-5, 5)
ax.set_ylim(0, None)
ax.set_xlabel('E − E$_\\mathrm{F}$ (eV)')
ax.set_ylabel('DOS (arb.)')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('pdos.pdf', format='pdf')
```

## Key Publication Rules

1. **NEVER MAKE UP DATA** - Read from files only
2. **NEVER plot same data twice** - One figure per dataset
3. **DOS orientation**: Energy on x-axis, DOS (arb.) on y-axis
4. **Broadening**: Always apply 0.03 eV Gaussian smoothing
5. **Figure width**: 3.5 in (single column)
6. **Font**: Arial, 8 pt
7. **Line width**: 0.5-0.6 pt
8. **Colors**: Muted palette (#2c3e50, #3498db, #e74c3c)
9. **Save as PDF** for vector graphics
10. **Remove** top/right spines
11. **Energy range**: -5 to 5 eV centered at Fermi
"""


BAND_STRUCTURE_PLOTTING = """
## Band Structure - Publication Quality

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': 0.5,
    'lines.linewidth': 0.6, 'figure.dpi': 300
})

data = qe_read_bands(output_dir)
k = np.array(data['k_distances'])
fermi = result['fermi_energy_eV']

fig, ax = plt.subplots(figsize=(3.5, 2.8))

for band in data['bands']:
    ax.plot(k, np.array(band) - fermi, color='#2c3e50', lw=0.6)

ax.axhline(0, color='#e74c3c', ls='--', lw=0.5, alpha=0.8)
ax.set_xlim(k[0], k[-1])
ax.set_ylim(-5, 5)
ax.set_xlabel('Wave vector')
ax.set_ylabel('E − E$_\\mathrm{F}$ (eV)')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('bands.pdf', format='pdf')
```
"""


DOS_PLOTTING = """
## DOS - Publication Quality (Energy on X-axis, 0.03 eV broadening)

```python
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d

plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': 0.5,
    'lines.linewidth': 0.6, 'figure.dpi': 300
})

data = qe_read_dos(output_dir)
E = np.array(data['energies']) - result['fermi_energy_eV']
dos = np.array(data['dos'])

# Apply 0.03 eV Gaussian broadening
de = abs(E[1] - E[0])
dos_smooth = gaussian_filter1d(dos, 0.03 / de)

fig, ax = plt.subplots(figsize=(3.5, 2.5))

ax.plot(E, dos_smooth, color='#2c3e50', lw=0.6)
ax.fill_between(E, 0, dos_smooth, color='#3498db', alpha=0.3)
ax.axvline(0, color='#e74c3c', ls='--', lw=0.5, alpha=0.8)

ax.set_xlim(-5, 5)
ax.set_ylim(0, None)
ax.set_xlabel('E − E$_\\mathrm{F}$ (eV)')
ax.set_ylabel('DOS (arb.)')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('dos.pdf', format='pdf')
```
"""


PDOS_PLOTTING = """
## PDOS - Publication Quality (Energy on X-axis, 0.03 eV broadening)

```python
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d

plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 8, 'axes.linewidth': 0.5,
    'lines.linewidth': 0.6, 'figure.dpi': 300
})

files = qe_list_files(output_dir)
fermi = result['fermi_energy_eV']
colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6']

fig, ax = plt.subplots(figsize=(3.5, 2.5))

for i, pf in enumerate(files['pdos_files'][:4]):
    data = qe_read_pdos(pf)
    E = np.array(data['energies']) - fermi
    ldos = np.array(data['ldos'])
    ldos_smooth = gaussian_filter1d(ldos, 0.03 / abs(E[1] - E[0]))
    ax.fill_between(E, 0, ldos_smooth, alpha=0.4, color=colors[i % 4])

ax.axvline(0, color='#e74c3c', ls='--', lw=0.5, alpha=0.8)
ax.set_xlim(-5, 5)
ax.set_ylim(0, None)
ax.set_xlabel('E − E$_\\mathrm{F}$ (eV)')
ax.set_ylabel('DOS (arb.)')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('pdos.pdf', format='pdf')
```
"""
