@echo off
setlocal
cd /d "%~dp0\..\.."

if exist ".git" (
  where git >nul 2>&1
  if not errorlevel 1 (
    git rm -r --ignore-unmatch "src/tester_zepto_pro" "scripts/Start-TesterZeptoPro.ps1"
    if not errorlevel 1 goto :done
  )
)

if exist "src\tester_zepto_pro" rmdir /s /q "src\tester_zepto_pro"
if exist "scripts\Start-TesterZeptoPro.ps1" del /f /q "scripts\Start-TesterZeptoPro.ps1"

:done
echo VibraPilot GitHub CI hygiene cleanup applied.
endlocal
