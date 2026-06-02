@echo off
cd /d "%~dp0"
echo Iniciando MaisNova Sport Trigger...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRO ao iniciar o aplicativo.
    echo Verifique se as dependencias estao instaladas: pip install -r requirements.txt
    pause
)
