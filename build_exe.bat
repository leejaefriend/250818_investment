@echo off
setlocal

REM ===== 경로/파이썬 설정 =====
REM venv를 쓰고 있다면 활성화
IF EXIST ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

REM 필수 패키지 (없으면 설치)
python -m pip install --upgrade pip
python -m pip install pyinstaller python-dotenv tensorboard

REM 런타임 라이브러리 (이미 설치되어 있으면 스킵됨)
REM torch는 CPU로만 설치되어 있어야 함(사용자 요구: CUDA X)
python -c "import torch" 2>NUL || python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -c "import stable_baselines3" 2>NUL || python -m pip install stable-baselines3
python -c "import gymnasium" 2>NUL || python -m pip install gymnasium
python -c "import pandas" 2>NUL || python -m pip install pandas
python -c "import numpy" 2>NUL || python -m pip install numpy
python -c "import matplotlib" 2>NUL || python -m pip install matplotlib
python -c "import requests" 2>NUL || python -m pip install requests

REM 깨끗이 빌드
rmdir /s /q build 2>NUL
rmdir /s /q dist  2>NUL
del bot.spec 2>NUL

REM ===== PyInstaller 빌드 =====
REM run_on_boot.py를 엔트리로 사용 (이 파일은 dist 폴더 안에서 .env 읽고 외부 train/trade 파일을 로드)
pyinstaller ^
  --noconfirm ^
  --clean ^
  --name bot ^
  --paths . ^
  --additional-hooks-dir hooks ^
  --collect-data stable_baselines3 ^
  --collect-data gymnasium ^
  --collect-data cloudpickle ^
  --collect-data pandas ^
  --collect-data matplotlib ^
  --collect-submodules torch ^
  --hidden-import stable_baselines3 ^
  --hidden-import gymnasium ^
  --hidden-import cloudpickle ^
  --hidden-import torch ^
  --add-data ".env;." ^
  --add-data "README.md;." ^
  run_on_boot.py

echo.
echo === BUILD DONE ===
echo dist\bot\bot.exe 를 실행하세요.
endlocal
