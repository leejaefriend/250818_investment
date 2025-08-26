@echo off
setlocal
cd /d %~dp0

set TASK_NAME=CryptoBotOnBoot
set TASK_NAME2=CryptoBotOnLogon
set START_BAT=%~dp0start_bot.bat

REM 기존 동일 이름 태스크 있으면 삭제
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
schtasks /Delete /TN "%TASK_NAME2%" /F >nul 2>&1

REM 1) 시스템 시작 시 (사용자 로그인 없어도)
schtasks /Create /TN "%TASK_NAME%" /TR "\"%START_BAT%\"" /SC ONSTART /RL HIGHEST /F

REM 2) 사용자 로그온 시 (보조 트리거)
schtasks /Create /TN "%TASK_NAME2%" /TR "\"%START_BAT%\"" /SC ONLOGON /RL HIGHEST /F

echo.
echo [OK] 작업 스케줄러 등록 완료.
echo 재부팅 후 자동으로 dist\bot.exe 실행됨.
endlocal
