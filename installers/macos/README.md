# macOS installer — Bibliometric Analysis System

**Repository:** https://github.com/LuisMRaimundo/Bibliometrics

## First-time install

1. In Terminal (from the project folder):

   ```bash
   chmod +x "installers/macos/INSTALL.command" installers/common/install-core.sh run.sh
   ```

2. Double-click **`installers/macos/INSTALL.command`** in Finder.

   If macOS blocks it: right-click → **Open**, or run in Terminal:

   ```bash
   ./installers/macos/INSTALL.command
   ```

The installer creates `.venv` and installs network, dashboard, and enrichment features.

## Run the app

```bash
./run.sh
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| “Unidentified developer” | Right-click `INSTALL.command` → **Open** |
| Python missing | Install from [python.org](https://www.python.org/downloads/) or `brew install python@3.12`, then run the installer again |
| Import errors | Re-run `installers/macos/INSTALL.command` |

Root-level `install-mac.command` forwards to the same install flow; use `installers/macos/INSTALL.command` for consistency with Windows/Linux paths.
