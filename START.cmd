@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3.13 "%~dp0launch.py"
) else (
  python "%~dp0launch.py"
)
if errorlevel 1 pause
