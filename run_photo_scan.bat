@echo off
REM Helper script to run local photo processing with Conda environment
REM Usage: run_photo_scan.bat [directory] [--target NAME] [--output DIR] [--copy]

echo Starting Photo Scan using JRock AI Vision Processor...
echo.

REM Activate generic Conda environment
call "C:\Users\jared\miniconda3\Scripts\activate.bat" base
if %ERRORLEVEL% NEQ 0 ( echo Failed to activate conda & exit /b 1 )

REM Run script using python directly
python "src\app\ingest\process_local_photos.py" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error running photo processor. Please check arguments or installation.
    pause
)
