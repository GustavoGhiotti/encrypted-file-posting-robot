@echo off
rem Caminho da raiz do projeto (um nivel acima da pasta start)
set "PROJECT_DIR=%~dp0.."

rem Muda para esse diretorio
cd /d "%PROJECT_DIR%"

:: (opcional) ativar venv
if exist "%PROJECT_DIR%\.venv\Scripts\activate.bat" (
  call "%PROJECT_DIR%\.venv\Scripts\activate.bat"
) else if exist "%PROJECT_DIR%\venv\Scripts\activate.bat" (
  call "%PROJECT_DIR%\venv\Scripts\activate.bat"
)

:: roda o script principal
python scripts\sirius_carga.py