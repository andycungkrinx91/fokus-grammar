@echo off
echo Starting Fokus Grammar Application...
echo.
echo Make sure LM Studio is running with a compatible model on http://127.0.0.1:1234
echo.

REM Check if Poetry is installed
where poetry >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Poetry is not installed or not in PATH.
    echo Please install Poetry from https://python-poetry.org/docs/#installation
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist and install dependencies
if not exist .venv (
    echo Setting up virtual environment and installing dependencies...
    poetry install
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM Run the application
echo Starting the application...
poetry run python app.py

pause
