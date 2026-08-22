@echo off
title ShareBox - Local Campus & Hostel Wi-Fi Hub
cls

echo ========================================================
echo   ⚡ Starting ShareBox Local Wi-Fi File Sharing Hub...
echo ========================================================
echo.

:: Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3 from https://www.python.org/
    pause
    exit /b 1
)

:: Run ShareBox
python sharebox.py %*

if %errorlevel% neq 0 (
    echo.
    echo ShareBox encountered an issue. Press any key to exit.
    pause
)
