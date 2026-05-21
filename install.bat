@echo off
REM Bibliometric Analysis System - Windows installer (forwards to installers\windows)
cd /d "%~dp0"
call "%~dp0installers\windows\INSTALL.bat"
exit /b %ERRORLEVEL%
