@echo off
title J.A.R.V.I.S. NATIVE OS - MARK XVII
color 0B
cd /d "%~dp0"
echo ===================================================================
echo   Initiating J.A.R.V.I.S. Native Desktop Operating System...
echo   Mark XVII - Personal ^& Business AI OS for Sir Shakil
echo ===================================================================

set "PYTHON_EXE=C:\Users\Qbits\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" run.py
) else (
    python run.py
)

if errorlevel 1 (
    echo.
    echo [ERROR] J.A.R.V.I.S. desktop application exited with code %errorlevel%.
    echo Press any key to inspect or close...
    pause >nul
)
