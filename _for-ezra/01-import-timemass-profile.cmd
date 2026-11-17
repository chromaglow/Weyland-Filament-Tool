@echo off
setlocal
rem One-click install of the TimePlast TimeMass presets into the Bambu Studio user folders:
rem three filament presets (Plant Vitamin, Fire, Detergent) and one process preset
rem (0.30mm TimeMass @BBL P1S 0.8 nozzle).
rem - Close Bambu Studio first (the script refuses to run while it is open).
rem - It asks before overwriting an existing preset of the same name.
cd /d "%~dp0.."
echo Installing the TimePlast TimeMass presets into Bambu Studio...
echo (Please close Bambu Studio first if it is open.)
echo.
set FAILED=0
call :install "" "TimePlast TimeMass Plant Vitamin"
call :install "" "TimePlast TimeMass Fire"
call :install "" "TimePlast TimeMass Detergent"
call :install "--process" "0.30mm TimeMass @BBL P1S 0.8 nozzle"
echo.
if "%FAILED%"=="1" (echo One or more presets were NOT installed. See the messages above.) else (echo Finished. All presets installed.)
pause
exit /b %FAILED%

:install
rem %~1 = optional flag (--process), %~2 = preset file name without .json
python -m src.install_profile %~1 "docs\research\timemass-plant-vitamin\%~2.json"
if errorlevel 1 set FAILED=1
echo.
exit /b 0
