@echo off
setlocal

REM ==== Paths ====
set PROJ_DIR=%~dp0
set DIST_DIR=%PROJ_DIR%dist
set VENV=%PROJ_DIR%.venv
set PYTHON=%VENV%\Scripts\python.exe
set PIP=%VENV%\Scripts\pip.exe

echo [BUILD] ensure venv...
if not exist "%VENV%" (
  py -3 -m venv "%VENV%"
)
echo [BUILD] install requirements...
"%PIP%" install --upgrade pip wheel setuptools
if exist "%PROJ_DIR%requirements.txt" (
  "%PIP%" install -r "%PROJ_DIR%requirements.txt"
) else (
  "%PIP%" install stable-baselines3==2.3.2 gymnasium torch pandas numpy matplotlib cloudpickle python-dotenv pyinstaller
)

echo [BUILD] clean dist/build...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%PROJ_DIR%build" rmdir /s /q "%PROJ_DIR%build%"

echo [BUILD] PyInstaller...
"%PYTHON%" -m PyInstaller ^
  --name bot ^
  --onefile ^
  --console ^
  --clean ^
  --noconfirm ^
  --add-data ".env.sample;." ^
  --additional-hooks-dir "%PROJ_DIR%" ^
  --hidden-import gymnasium ^
  --hidden-import cloudpickle ^
  --hidden-import torch ^
  --exclude-module cudnn ^
  --exclude-module torch.cuda ^
  "%PROJ_DIR%run_on_boot.py"

echo [BUILD] move exe to dist...
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
move /y "%PROJ_DIR%dist\bot.exe" "%DIST_DIR%\bot.exe" >nul

echo [BUILD] done. exe: %DIST_DIR%\bot.exe
endlocal
