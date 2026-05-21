# Installers - Bibliometric Analysis System

**Repository:** https://github.com/LuisMRaimundo/Bibliometrics

| Platform | Entry point |
|----------|-------------|
| **Windows 10/11** | `installers/windows/INSTALL.bat` or root `install.bat` |
| **macOS** | `installers/macos/INSTALL.command` (or root `install-mac.command`) |
| **Linux** | `installers/linux/install.sh` (or root `install.sh`) |

Shared install logic: `installers/common/install-core.sh` (venv + `pip install -e ".[network,dashboard,enrichment]"`).

| Folder | Docs |
|--------|------|
| `installers/windows/` | `installers/windows/README.md` |
| `installers/macos/` | `installers/macos/README.md` |
| `installers/linux/` | `installers/linux/README.md` |

See also root `INSTALL.md` for platform notes and troubleshooting.
