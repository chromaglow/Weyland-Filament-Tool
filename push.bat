@echo off
echo ========================================
echo  Pushing to GitHub
echo ========================================
echo.

cd /d "%~dp0"

echo Pushing bambu-filament-tool to GitHub...
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo ========================================
    echo  Push failed!
    echo ========================================
    echo.
    echo Make sure you created the repository on GitHub first:
    echo 1. Go to https://github.com/new
    echo 2. Name: bambu-filament-tool
    echo 3. Public, no README/license/gitignore
    echo 4. Click "Create repository"
    echo.
    echo Then run this script again.
    pause
) else (
    echo.
    echo ========================================
    echo  SUCCESS!
    echo ========================================
    echo.
    echo Your repository is now live at:
    echo https://github.com/chromaglow/bambu-filament-tool
    echo.
    pause
)
