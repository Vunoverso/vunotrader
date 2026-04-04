@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\iniciar-vuno-robo.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo O Vuno Robo encerrou com codigo %EXIT_CODE%.
  pause
)
endlocal & exit /b %EXIT_CODE%