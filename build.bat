@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ============================================
echo  MaisNova Sport Trigger - Build .EXE
echo ============================================
echo.

REM ── Lê a versão direto do version.py ────────────────────────────────────
for /f "tokens=*" %%i in ('python -c "from version import __version__; print(__version__)"') do set APP_VERSION=%%i
echo Versao detectada: v%APP_VERSION%
echo.

REM ── Gera ícone atualizado ────────────────────────────────────────────────
echo.
echo [1/4] Gerando icone...
python create_icon.py
if %ERRORLEVEL% NEQ 0 (
    echo AVISO: Falha ao gerar icone — usando icone existente.
)

REM ── Dependências ────────────────────────────────────────────────────────
echo [2/4] Instalando dependencias...
pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERRO ao instalar dependencias.
    pause
    exit /b 1
)

REM ── Build ────────────────────────────────────────────────────────────────
echo.
echo [2/4] Compilando SportTrigger.exe v%APP_VERSION%...
echo NOTA: O VLC deve estar instalado no PC onde o .exe vai rodar.
echo.

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "SportTrigger" ^  --icon "assets\icon.ico" ^  --version-file "version_info.txt" ^
  --add-data "config.json;." ^
  --add-data "assets;assets" ^
  --hidden-import "pycaw" ^
  --hidden-import "comtypes.stream" ^
  --hidden-import "watchdog.observers.winapi" ^
  --hidden-import "customtkinter" ^
  --hidden-import "requests" ^
  --collect-all "customtkinter" ^
  --collect-all "pystray" ^
  main.py

if %ERRORLEVEL% NEQ 0 (
    echo ERRO durante a compilacao.
    pause
    exit /b 1
)

REM ── Renomear com versão ──────────────────────────────────────────────────
echo.
echo [3/4] Preparando release...
if exist "dist\SportTrigger_v%APP_VERSION%.exe" del "dist\SportTrigger_v%APP_VERSION%.exe"
copy "dist\SportTrigger.exe" "dist\SportTrigger_v%APP_VERSION%.exe" >NUL
echo Executavel versionado: dist\SportTrigger_v%APP_VERSION%.exe

REM ── Publicar no GitHub Releases ──────────────────────────────────────────
echo.
echo [4/4] Publicando GitHub Release v%APP_VERSION%...
echo.

REM Verifica se gh CLI está disponível
where gh >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo AVISO: GitHub CLI (gh) nao encontrado. Publique manualmente:
    echo   1. Acesse https://github.com/RobsonDV/maisnova-sport-trigger/releases/new
    echo   2. Tag: v%APP_VERSION%
    echo   3. Faça upload de: dist\SportTrigger.exe
    goto :done
)

REM Cria a tag localmente (se não existir)
git tag "v%APP_VERSION%" 2>NUL

REM Publica o release com o .exe como asset
gh release create "v%APP_VERSION%" ^
  "dist\SportTrigger.exe#SportTrigger.exe" ^
  --title "v%APP_VERSION%" ^
  --notes-file RELEASE_NOTES.md 2>NUL || ^
gh release create "v%APP_VERSION%" ^
  "dist\SportTrigger.exe#SportTrigger.exe" ^
  --title "v%APP_VERSION%" ^
  --generate-notes

REM Se o instalador Inno Setup existir, adiciona ao release também
if exist "dist\MaisNova_SportTrigger_Setup_v%APP_VERSION%.exe" (
    gh release upload "v%APP_VERSION%" ^
      "dist\MaisNova_SportTrigger_Setup_v%APP_VERSION%.exe#MaisNova_SportTrigger_Setup_v%APP_VERSION%.exe" ^
      --clobber
    echo Instalador adicionado ao release.
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Release v%APP_VERSION% publicado com sucesso!
    echo https://github.com/RobsonDV/maisnova-sport-trigger/releases
) else (
    echo AVISO: Erro ao publicar release automaticamente.
    echo Publique manualmente em: https://github.com/RobsonDV/maisnova-sport-trigger/releases/new
    echo Tag: v%APP_VERSION%  ^|  Asset: dist\SportTrigger.exe
)

:done
echo.
echo ============================================
echo  Build concluido: dist\SportTrigger.exe
echo  Versao: v%APP_VERSION%
echo ============================================
echo.
echo IMPORTANTE: Copie o config.json para a mesma pasta do .exe antes de executar pela primeira vez.
echo.
pause

