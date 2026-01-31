@echo off
echo ===============================================
echo  Bambu Filament Profile Generator
echo  Starting application...
echo ===============================================
echo.

python src\main.py

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start application
    echo Make sure Python is installed and dependencies are installed:
    echo    pip install -r requirements.txt
    pause
)
