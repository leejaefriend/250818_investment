@echo off
echo [INFO] upgrade pip
python -m pip install --upgrade pip wheel

echo [INFO] install requirements.txt
pip install -r requirements.txt

echo [INFO] clean build folders
rmdir /s /q build dist __pycache__ >nul 2>&1

echo [INFO] build start
pyinstaller --onefile ^
  --hidden-import numpy ^
  --hidden-import stable_baselines3 ^
  --hidden-import torch ^
  --hidden-import gymnasium ^
  --hidden-import pandas ^
  --hidden-import pyupbit ^
  --add-data "%VIRTUAL_ENV%\Lib\site-packages\stable_baselines3\version.txt;stable_baselines3" ^
  bot.py

if %errorlevel% neq 0 (
    echo [ERROR] build failed
    exit /b %errorlevel%
)

echo [INFO] build success
