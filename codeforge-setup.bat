@echo off
rem ==============================================================================
rem CodeForge — Windows Turnkey Installer Launcher
rem Double-click this file to launch the automated setup script.
rem ==============================================================================
title CodeForge Turnkey Installer
echo Launching CodeForge Turnkey Setup via PowerShell...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0codeforge-setup.ps1" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup encountered an issue. See details above.
    pause
) else (
    echo.
    echo Press any key to close this installer window.
    pause >nul
)
