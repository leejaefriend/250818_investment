@echo off
setlocal

echo [INFO] upgrade pip
python -m pip install --upgrade pip wheel pyinstaller python-dotenv

echo [INFO] install requirements.txt
pip install -r requirements.txt

echo [INFO] clean build folders
rmdir /s /q build dist __pycache__ 2>nul
del /q *.spec 2>nul

echo [INFO] build start
pyinstaller --onefile ^
  --hidden-import train ^
  --hidden-import trade_hourly ^
  --hidden-import upbit_exec ^
  bot.py

if %errorlevel% neq 0 (
  echo [ERROR] build failed
  exit /b %errorlevel%
)

echo [INFO] build success
endlocal
