@echo off
REM Ejecuta todos los tests. Usar desde cmd (no PowerShell).
cd /d "%~dp0"
python tests/run_tests.py
pause
