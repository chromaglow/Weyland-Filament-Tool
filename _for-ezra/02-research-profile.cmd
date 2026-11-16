@echo off
setlocal EnableDelayedExpansion
rem One-click research or import of a filament profile.
rem - Research: collects settings from a manufacturer page and a community profile, merges them.
rem - Import: reads a profile file you already have (Bambu or Orca) and re-exports it.
rem - Output goes to output\research\<material>\ under the project folder (output\ is git-ignored).
rem - Nothing is installed into Bambu Studio unless you say yes at the very end.
rem   Close Bambu Studio before you say yes.
cd /d "%~dp0.."
echo ============================================================
echo  Research or import a filament profile
echo  Press Enter to accept the value in [brackets].
echo ============================================================
echo.
set MODE=
set /p MODE=Do you want to [R]esearch online or [I]mport a file? [R]: 
if /i "!MODE!"=="I" (set MODE=import) else (set MODE=research)
echo.
set "MATERIAL=Plant Vitamin"
set /p MATERIAL=Material name [Plant Vitamin]: 
set "MAKER=TimePlast"
set /p MAKER=Manufacturer [TimePlast]: 
set "MATSLUG=!MATERIAL: =-!"
set "OUT=output\research\!MATSLUG!"
set "NAME=!MAKER! !MATERIAL!"
set FAILED=0

if "!MODE!"=="import" goto :doimport

set "PAGE=https://www.timeplast.com/shop/p/timemass-plant-vitamin-filament"
set /p PAGE=Manufacturer product page URL [%PAGE%]: 
set "COMM=OrcaSlicer/OrcaSlicer:resources/profiles/BBL/filament/Bambu PLA Basic @BBL P1S 0.4 nozzle.json"
set /p COMM=Community profile, owner/repo:path [Bambu PLA Basic on OrcaSlicer]: 
echo.
echo Researching. This reads two web pages. It can take a minute...
echo.
python -m src.research_profile research --material "!MATERIAL!" --manufacturer "!MAKER!" --name "!NAME!" --source "manufacturer=!PAGE!" --source "community=!COMM!" --out "!OUT!"
if errorlevel 1 set FAILED=1
goto :finished

:doimport
set "FILE="
set /p FILE=Full path of the profile file to import (.json): 
if "!FILE!"=="" (
  echo No file given. Nothing to do.
  set FAILED=1
  goto :finished
)
set "FILE=!FILE:"=!"
echo.
python -m src.research_profile import "!FILE!" --manufacturer "!MAKER!" --name "!NAME!" --out "!OUT!"
if errorlevel 1 set FAILED=1

:finished
echo.
if "!FAILED!"=="1" (
  echo FAILED. Nothing was installed. Read the message above.
  echo If it says offline or not in the cache, check your internet connection and try again.
  pause
  exit /b 1
)
echo Finished. Files were written to: %CD%\!OUT!
echo Open the .report.md file there to see where each value came from.
start "" explorer "%CD%\!OUT!"
echo.
set INSTALL=N
set /p INSTALL=Install into Bambu Studio now? [y/N]: 
if /i not "!INSTALL!"=="Y" (
  echo Not installed. You can run this again later and answer y.
  pause
  exit /b 0
)
echo.
echo Please make sure Bambu Studio is closed. Installing...
if "!MODE!"=="import" (
  python -m src.research_profile import "!FILE!" --manufacturer "!MAKER!" --name "!NAME!" --out "!OUT!" --install
) else (
  python -m src.research_profile research --material "!MATERIAL!" --manufacturer "!MAKER!" --name "!NAME!" --source "manufacturer=!PAGE!" --source "community=!COMM!" --out "!OUT!" --install
)
if errorlevel 1 (
  echo Install FAILED or was declined. See the message above.
  pause
  exit /b 1
)
echo Install step finished. Start Bambu Studio and look for "!NAME!".
pause
exit /b 0
