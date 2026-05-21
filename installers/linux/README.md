# Linux installer — Bibliometric Analysis System

**Repository:** https://github.com/LuisMRaimundo/Bibliometrics

## First-time install

```bash
chmod +x installers/linux/install.sh installers/common/install-core.sh run.sh
./installers/linux/install.sh
```

The script creates `.venv` in the project folder and installs the package with network, dashboard, and enrichment extras.

## Run the app

```bash
./run.sh
```

Or: `.venv/bin/python software_gui_pro_4.py`

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Python 3.10+ not found | `sudo apt install python3 python3-venv python3-pip` (Debian/Ubuntu) or use your distro’s package manager |
| Permission denied | Run `chmod +x` on the installer and `run.sh` as shown above |
| Import errors | Re-run `./installers/linux/install.sh` |

Root-level `./install.sh` is equivalent; prefer `installers/linux/install.sh` for consistency with other platforms.
