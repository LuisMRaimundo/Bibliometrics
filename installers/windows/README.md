# Bibliometric Analysis System - Windows installation

**Repository:** https://github.com/LuisMRaimundo/Bibliometrics

## Standard installation (no Python required)

1. Download a **fresh** ZIP from GitHub (**Code -> Download ZIP**) or clone the repo.
2. Open **`installers\windows`** OR double-click **`install.bat`** at the repository root (same installer).
3. Double-click **`INSTALL.bat`** or **`START-HERE.bat`**.
4. Wait for **SUCCESS** or **Done** (first run: **10-25 minutes**).
5. Start the app with **`run.bat`** at the project root.

## Install log

`install.log` in the project root.

## Troubleshooting

| Issue | Action |
|-------|--------|
| No window / closes instantly | Re-download from GitHub; run **`INSTALL.bat`**. Never use `>>>` in batch echo lines. |
| PowerShell parse error | Old copy with Unicode characters; download fresh from GitHub. |
| Python error | Install Python 3.10+ from https://www.python.org/downloads/ with **Add to PATH**, then run **`INSTALL.bat`** again. |
| pip failed | Open `install.log`, delete `.venv`, retry. |
