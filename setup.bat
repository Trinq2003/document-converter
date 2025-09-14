@echo off
REM Setup script for Document Converter API

echo 🚀 Setting up Document Converter API...

REM Check if uv is installed
uv --version >nul 2>&1
if errorlevel 1 (
    echo ❌ uv is not installed. Please install it first:
    echo    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    exit /b 1
)

echo ✅ uv is installed

REM Generate lock file
echo 📦 Generating lock file...
uv lock

echo ✅ Lock file generated

REM Install dependencies
echo 📥 Installing dependencies...
uv sync --no-install-project

echo ✅ Dependencies installed

REM Install pre-commit hooks (if in dev mode)
if "%1"=="--dev" (
    echo 🔧 Installing pre-commit hooks...
    uv run pre-commit install
    echo ✅ Pre-commit hooks installed
)

echo 🎉 Setup complete!
echo.
echo Next steps:
echo   make dev     # Run development server
echo   make test    # Run tests
echo   make docker-build  # Build Docker image
