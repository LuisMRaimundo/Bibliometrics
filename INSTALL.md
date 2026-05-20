# Installation (no Python experience required)

Repository: [github.com/LuisMRaimundo/Bibliometrics](https://github.com/LuisMRaimundo/Bibliometrics)

## One-click install

| Platform | Step 1 — Install | Step 2 — Run |
|----------|------------------|--------------|
| **Windows 10/11** | Double-click **`install.bat`** | Double-click **`run.bat`** |
| **macOS** | Double-click **`install-mac.command`** (first time: right-click → Open if Gatekeeper blocks) | Run **`run.sh`** in Terminal, or `.venv/bin/python software_gui_pro_4.py` |
| **Linux** | In Terminal: `chmod +x install.sh run.sh && ./install.sh` | `./run.sh` |

Installers create a local **`.venv`** folder with all Python packages. You do **not** need to configure Python manually if the installer succeeds.

### Windows notes

- If Python is missing, the installer tries **winget** (`Python.Python.3.12`).
- If winget is unavailable, download Python from [python.org](https://www.python.org/downloads/) and check **“Add python.exe to PATH”**, then run `install.bat` again.

### macOS notes

- If Python is missing, the installer tries **Homebrew** (`brew install python@3.12`).
- Without Homebrew, install Python from [python.org](https://www.python.org/downloads/).

### Linux notes

- The installer tries `apt`, `dnf`, or `pacman` (may ask for your `sudo` password).
- On minimal systems, install `python3`, `python3-venv`, and `python3-pip` first.

## What gets installed

Core bibliometric pipeline plus optional features used by the GUI tool buttons:

- Network visualization (PyVis, Louvain/Leiden)
- Streamlit dashboard and pipeline runner
- Entity enrichment (OpenAlex)

Heavy optional topic modelling (`bertopic`, etc.) is **not** installed by default. Developers can run:

```bash
.venv/bin/pip install -e ".[all]"
```

## OpenAlex email

When using online features, enter a valid **mailto** address (e.g. `you@university.edu`) in the GUI. OpenAlex asks for this for polite API use.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `install.bat` says Python not found | Install Python 3.10+, reopen terminal, run `install.bat` again |
| Import errors when running | Re-run the installer for your platform |
| Streamlit buttons fail | Re-run installer (includes `dashboard` extras) |
| macOS “unidentified developer” | Right-click `install-mac.command` → **Open** |

## For developers

```bash
git clone https://github.com/LuisMRaimundo/Bibliometrics.git
cd Bibliometrics
pip install -e ".[dev,enrichment,network,dashboard]"
pytest tests/ -q
```
