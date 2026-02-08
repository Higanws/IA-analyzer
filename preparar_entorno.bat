@echo off
REM IA Analyzer — Preparar entorno (y opciones: descargar modelo, tests, build)
REM Los scripts de entorno están en entorno\ (install_llm.py, etc.)
REM Uso: preparar_entorno.bat [install-llm | download-model | test | build]
REM Sin argumentos: muestra menú.

cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel% equ 0 (set PY=py -3) else (set PY=python)

if "%~1"=="" goto menu
if /i "%~1"=="install-llm"   goto install_llm
if /i "%~1"=="download-model" goto download_model
if /i "%~1"=="test"           goto test
if /i "%~1"=="build"          goto build
echo Opcion no valida: %~1. Use: install-llm, download-model, test, build
pause
exit /b 1

:menu
echo.
echo  IA Analyzer — Preparar entorno
echo  1. Instalar LLM (deps + modelo + llama-cpp-python)
echo  2. Descargar modelo GGUF (solo)
echo  3. Ejecutar tests
echo  4. Compilar a .exe
echo  5. Salir
echo.
set /p opt="Elija 1-5: "
if "%opt%"=="1" goto install_llm
if "%opt%"=="2" goto download_model
if "%opt%"=="3" goto test
if "%opt%"=="4" goto build
if "%opt%"=="5" exit /b 0
goto menu

:install_llm
echo.
echo >>> Instalando LLM (entorno\install_llm.py)...
%PY% entorno\install_llm.py
goto end

:download_model
echo.
echo >>> Descargando modelo Qwen 0.5B a models/...
%PY% entorno\install_llm.py --download-only
goto end

:test
echo.
echo >>> Ejecutando tests...
%PY% tests\run_tests.py
goto end

:build
echo.
echo >>> Compilando a .exe (PyInstaller --onedir)...
%PY% -m PyInstaller --name IA_Analyzer --windowed --onedir app.py
if errorlevel 1 (
    echo ERROR: PyInstaller fallo. Instale con: pip install pyinstaller
    pause
    exit /b 1
)
echo Limpiando temporales...
for /d /r %%i in (__pycache__) do if exist "%%i" rmdir /s /q "%%i" 2>nul
if exist build rmdir /s /q build
if exist IA_Analyzer.spec del /f /q IA_Analyzer.spec
if exist config\config.json (
    if not exist "dist\IA_Analyzer\config" mkdir "dist\IA_Analyzer\config"
    copy /Y config\config.json "dist\IA_Analyzer\config\config.json" >nul
)
if not exist "dist\IA_Analyzer\models" mkdir "dist\IA_Analyzer\models"
echo.
echo Compilacion OK. Ejecutable: dist\IA_Analyzer\IA_Analyzer.exe
echo Coloque el .gguf en dist\IA_Analyzer\models\ y model_path en config.json
goto end

:end
echo.
pause
