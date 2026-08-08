@echo off
setlocal
set "ROOT=%~dp0..\.."
pushd "%ROOT%" >nul || exit /b 1

if exist "src\tester_zepto_pro" rmdir /s /q "src\tester_zepto_pro"
if exist "scripts\Start-TesterZeptoPro.ps1" del /f /q "scripts\Start-TesterZeptoPro.ps1"

python scripts\verify_repository.py
if errorlevel 1 (
  popd >nul
  exit /b 1
)

set "PYTHONPATH=%CD%\src"
python -m unittest discover -s tests -v
set "RC=%ERRORLEVEL%"
popd >nul
exit /b %RC%
