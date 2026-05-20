@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM Bibliometric Analysis System v16 — start main GUI (software_gui_pro_4.py)

set "PYTHON="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON=%~dp0.venv\Scripts\python.exe"
    goto :run
)

where py >nul 2>&1 && set "PYTHON=py"
if not defined PYTHON where python >nul 2>&1 && set "PYTHON=python"

if not defined PYTHON (
    echo Python not found.
    echo Run install.bat first ^(one-click installer^).
    pause
    exit /b 1
)

:run
echo Starting Bibliometric Analysis System...
echo Folder: %CD%
echo.

"%PYTHON%" "%~dp0software_gui_pro_4.py"
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
    echo.
    echo The application exited with code %ERR%.
    echo If you see import errors, run install.bat to install dependencies.
    pause
    exit /b %ERR%
)

endlocal
