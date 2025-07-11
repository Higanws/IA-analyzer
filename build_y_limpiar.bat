@echo off
REM 🛠 Compilar IA_Analyzer como monolito y limpiar __pycache__

cd /d "%~dp0"

set PYI="%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts\pyinstaller.exe"

echo ▶️ Compilando IA_Analyzer...
%PYI% --name IA_Analyzer --windowed app.py

echo 🧹 Limpiando __pycache__ y archivos temporales...
for /d /r %%i in (__pycache__) do if exist "%%i" rmdir /s /q "%%i"
if exist build rmdir /s /q build
if exist IA_Analyzer.spec del /f /q IA_Analyzer.spec

REM Copiar config.json al build final
if exist config\config.json (
    mkdir dist\IA_Analyzer\config >nul 2>&1
    copy /Y config\config.json dist\IA_Analyzer\config\config.json >nul
)

echo ✅ Compilación finalizada. Ejecutable disponible en dist\IA_Analyzer\IA_Analyzer.exe
pause
