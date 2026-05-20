@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo  Bibliometric Analysis System v16 - Windows Installer
echo  Windows 10 / 11
echo ============================================================
echo.

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    echo Virtual environment already exists. Updating packages...
    goto :install_packages
)

set "PYEXE="
where py >nul 2>&1 && (
    py -3 --version >nul 2>&1 && set "PYEXE=py -3"
)
if not defined PYEXE where python >nul 2>&1 && set "PYEXE=python"

if not defined PYEXE (
    echo Python 3.10+ not found on this PC.
    echo.
    echo Attempting automatic install with winget...
    where winget >nul 2>&1
    if errorlevel 1 goto :need_manual_python
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto :need_manual_python
    echo.
    echo Python was installed. If this window still cannot find Python,
    echo close it, open a NEW Command Prompt, and run install.bat again.
    where py >nul 2>&1 && set "PYEXE=py -3"
    if not defined PYEXE where python >nul 2>&1 && set "PYEXE=python"
)

if not defined PYEXE goto :need_manual_python

echo Using: %PYEXE%
echo Creating virtual environment in .venv ...
%PYEXE% -m venv "%~dp0.venv"
if errorlevel 1 (
    echo Failed to create virtual environment.
    goto :fail
)

:install_packages
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo Virtual environment is missing. Delete the .venv folder and run install again.
    goto :fail
)

echo Upgrading pip...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo Installing Bibliometric Analysis System and optional features...
"%VENV_PY%" -m pip install -e ".[network,dashboard,enrichment]"
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo  Installation complete!
echo.
echo  To start the application: double-click run.bat
echo  (or run run.bat from this folder)
echo ============================================================
pause
exit /b 0

:need_manual_python
echo.
echo Please install Python 3.10 or newer:
echo   https://www.python.org/downloads/
echo.
echo During setup, CHECK "Add python.exe to PATH".
echo Then run install.bat again.
pause
exit /b 1

:fail
echo.
echo Installation failed. See messages above.
pause
exit /b 1
