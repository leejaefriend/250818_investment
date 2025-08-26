@echo off
setlocal
cd /d %~dp0

REM (선택) 가상환경 활성화
REM call .venv\Scripts\activate

py -3 -m pip install -U pip wheel
py -3 -m pip install pyinstaller python-dotenv

REM 필요한 러ntime 라이브러리(예: sb3, gymnasium, pyupbit 등)는
REM 이미 프로젝트에 설치돼 있다고 가정. onefile이므로 collect-all로 끌어온다.
REM 로컬 .py 파일들은 --add-data로 반드시 포함해야 함.
REM 아래 목록에 네 프로젝트의 로컬 파이썬 파일들을 추가해라.
set DATA_LIST=train.py;.^
;trade_hourly.py;.^
;upbit_exec.py;.^
;features.py;.^
;env_utils.py;.^
;common.py;.

REM 위 목록에 없는 파일이 있으면 같은 형식으로 계속 추가:
REM   ;파일명.py;.

py -3 -m PyInstaller --clean --noconfirm ^
  --onefile ^
  --name bot ^
  --console ^
  --collect-all torch ^
  --collect-all stable_baselines3 ^
  --collect-all gymnasium ^
  --collect-all pyupbit ^
  --collect-all pandas ^
  --collect-all numpy ^
  --collect-all python_dotenv ^
  %FORCE_CONSOLE% ^
  --add-data "%DATA_LIST%" ^
  run_on_boot.py

echo.
echo [OK] 빌드 완료: dist\bot.exe
echo 실행은 dist\bot.exe 옆에 .env가 있어야 함
endlocal
