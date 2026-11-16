@echo off
setlocal
rem One-click install of the three TimePlast TimeMass filament presets
rem (Plant Vitamin, Fire, Detergent) into the Bambu Studio user filament folder.
rem - Close Bambu Studio first (the script refuses to run while it is open).
rem - It asks before overwriting an existing preset of the same name.
cd /d "%~dp0.."
echo Installing the TimePlast TimeMass presets into Bambu Studio...
echo (Please close Bambu Studio first if it is open.)
echo.
set FAILED=0
call :install "TimePlast TimeMass Plant Vitamin"
call :install "TimePlast TimeMass Fire"
call :install "TimePlast TimeMass Detergent"
echo.
if %FAILED%==1 (echo One or more presets were not installed. See the messages above.) else (echo Finished.)
pause
exit /b

:install
python -m src.install_profile "docs\research\timemass-plant-vitamin\%~1.json"
if errorlevel 1 set FAILED=1
echo.
exit /b
