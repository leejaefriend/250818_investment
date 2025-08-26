@echo off
setlocal
cd /d %~dp0
REM 로그 남기고 싶으면 아래처럼 추가
REM start "" "%~dp0dist\bot.exe" > "%~dp0runtime.log" 2>&1
start "" "%~dp0dist\bot.exe"
endlocal
