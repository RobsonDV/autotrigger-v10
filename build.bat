@echo off
cd /d "%~dp0"

echo ============================================
echo  MaisNova Sport Trigger - Build .EXE
echo ============================================
echo.

echo [1/3] Instalando dependencias...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERRO ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo [2/3] Compilando executavel...
echo NOTA: O VLC deve estar instalado no PC onde o .exe vai rodar.
echo.

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "SportTrigger" ^
  --add-data "config.json;." ^
  --hidden-import "pycaw" ^
  --hidden-import "comtypes.stream" ^
  --hidden-import "watchdog.observers.winapi" ^
  --hidden-import "customtkinter" ^
  --collect-all "customtkinter" ^
  --collect-all "pystray" ^
  main.py

if %ERRORLEVEL% NEQ 0 (
    echo ERRO durante a compilacao.
    pause
    exit /b 1
)

echo.
echo [3/3] Concluido!
echo Executavel gerado em: dist\SportTrigger.exe
echo.
echo IMPORTANTE: Copie o config.json para a mesma pasta do .exe antes de executar.
echo.
pause
