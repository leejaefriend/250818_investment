@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0

if not exist .venv (
  py -3 -m venv .venv
)

call .venv\Scripts\activate
python -m pip install -U pip wheel setuptools

REM 런처가 외부 py를 로드하므로 필수 러ntime만 설치
pip install "numpy<2.0" pandas pyupbit python-dotenv gymnasium stable-baselines3 pyinstaller
REM torch CPU가 필요하면 주석 해제:
REM pip install --index-url https://download.pytorch.org/whl/cpu torch

if exist build rd /s /q build
if exist dist rd /s /q dist
if exist bot.spec del /f /q bot.spec

pyinstaller -F -n bot --clean run_on_boot.py

if errorlevel 1 (
  echo [ERROR] 빌드 실패
  exit /b 1
)

echo [OK] 빌드 완료: dist\bot.exe
exit /b 0
