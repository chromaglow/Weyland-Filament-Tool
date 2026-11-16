@echo off
setlocal
rem One-click install of the TimePlast TimeMass Plant Vitamin filament preset
rem into the Bambu Studio user filament folder.
rem - Close Bambu Studio first (the script refuses to run while it is open).
rem - It asks before overwriting an existing preset of the same name.
cd /d "%~dp0.."
echo Installing TimePlast TimeMass Plant Vitamin into Bambu Studio...
echo (Please close Bambu Studio first if it is open.)
echo.
python -m src.install_profile "docs\research\timemass-plant-vitamin\TimePlast TimeMass Plant Vitamin.json"
echo.
if errorlevel 1 (echo Nothing was installed. See the messages above.) else (echo Finished.)
pause
