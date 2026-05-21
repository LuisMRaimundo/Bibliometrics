@echo off
setlocal EnableExtensions
title Bibliometrics - Installer
cd /d "%~dp0\..\.." || (
  echo ERROR: Cannot find project root.
  pause
  exit /b 1
)

echo.
echo  *** USE THIS FILE FOR NORMAL INSTALL ***
echo.
echo  ============================================================
echo   Bibliometric Analysis System v16 - Windows Installer
echo  ============================================================
echo.
echo  GitHub: https://github.com/LuisMRaimundo/Bibliometrics
echo.
echo  Do not close this window until finished.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-Easy.ps1"
set ERR=%ERRORLEVEL%

echo.
if %ERR% NEQ 0 (
  echo Installation failed. See install.log in the project folder.
) else (
  echo Done.
)
echo.
pause
exit /b %ERR%
