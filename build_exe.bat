@echo off
REM =========================
REM  build_exe.bat (full)
REM  - OneFile exe 빌드
REM  - train.py, trade_hourly.py를 강제로 포함 (--hidden-import)
REM  - .venv 사용 (없으면 자동 생성)
REM =========================

setlocal ENABLEDELAYEDEXPANSION

REM 프로젝트 루트(이 bat가 있는 위치)
set ROOT=%~dp0
cd /d "%ROOT%"

REM ---------- 가상환경 ----------
set VENV_DIR=.venv
set PY=%VENV_DIR%\Scripts\python.exe
set PIP=%VENV_DIR%\Scripts\pip.exe

if not exist "%PY%" (
  echo [INFO] create venv
  py -3 -m venv "%VENV_DIR%"
)

echo [INFO] upgrade pip & install build deps
"%PIP%" install -U pip wheel
"%PIP%" install -U pyinstaller python-dotenv

REM requirements.txt가 있으면 거기도 설치 (없어도 무시)
if exist requirements.txt (
  echo [INFO] install requirements.txt
  "%PIP%" install -r requirements.txt
)

REM ---------- 정리 ----------
echo [INFO] clean build folders
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

REM ---------- PyInstaller 옵션 ----------
set COMMON_OPTS=--noconfirm --clean --log-level=WARN
REM 콘솔 창 유지(로그 확인용). 콘솔 숨기려면 --noconsole 로 변경
set UI_OPTS=--console
set ONEFILE_OPTS=--onefile --name bot

REM ★ 누락 방지용 hidden-import (필요 모듈 더 있으면 공백으로 이어 붙여 추가)
set HIDDEN_IMP_OPTS=^
 --hidden-import train ^
 --hidden-import trade_hourly ^
 --hidden-import upbit_exec

REM 데이터 파일(필요 시 추가 예시)
REM --add-data "configs\config.ini;configs" 처럼 세미콜론 앞은 소스 경로, 뒤는 exe 내부 경로
set DATA_OPTS=

REM ---------- 빌드 실행 ----------
echo [INFO] build start
"%PY%" -m PyInstaller %COMMON_OPTS% %UI_OPTS% %ONEFILE_OPTS% %HIDDEN_IMP_OPTS% %DATA_OPTS% bot.py

if errorlevel 1 (
  echo [ERROR] build failed
  exit /b 1
)

echo [INFO] build done. dist\bot.exe 생성

REM ---------- 실행 보조 스크립트(더블클릭용) ----------
(
  echo @echo off
  echo cd /d "%%~dp0"
  echo start "" ".\bot.exe"
) > "dist\run_bot.cmd"

echo [INFO] run script created: dist\run_bot.cmd
echo [INFO] Done.

endlocal
