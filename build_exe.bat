@echo off
setlocal

REM ===== 경로/파이썬 지정 =====
set PROJ=%~dp0
pushd "%PROJ%"

REM 가상환경 파이썬
set VENV_PY=.\.venv\Scripts\python.exe

echo [INFO] upgrade pip
"%VENV_PY%" -m pip install --upgrade pip wheel

echo [INFO] install requirements.txt
"%VENV_PY%" -m pip install -r requirements.txt

echo [INFO] clean build folders
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
del /q /f *.spec 2>nul

echo [INFO] build start

REM === PyInstaller 옵션 ===
REM --hidden-import 로 내부 모듈(train, trade_hourly) 강제 포함
REM --add-data 로 .env/설정 파일 같이 포장하고 싶으면 여기 추가 (예: ".env;.")
"%VENV_PY%" -m PyInstaller ^
  --onefile ^
  --name bot ^
  --hidden-import train ^
  --hidden-import trade_hourly ^
  bot.py

if errorlevel 1 (
  echo [ERROR] build failed
  popd
  exit /b 1
)

echo [INFO] build success: .\dist\bot.exe
popd
endlocal
