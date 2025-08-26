@echo off
set TASK_NAME=CryptoBotOnBoot
set TASK_NAME2=CryptoBotOnLogon
schtasks /Delete /TN "%TASK_NAME%" /F
schtasks /Delete /TN "%TASK_NAME2%" /F
echo [OK] 자동실행 해제
