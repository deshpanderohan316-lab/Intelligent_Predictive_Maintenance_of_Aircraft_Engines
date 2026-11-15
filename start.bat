@echo off
REM One-click launcher: opens the Flask API and the Next.js UI in two separate windows.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run:  python -m venv .venv  ^&^&  .venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
if not exist "artifacts\models\best_model.joblib" (
  echo No trained model found - running the ML pipeline first...
  ".venv\Scripts\python.exe" -m ml.scripts.run_all || (pause & exit /b 1)
)
if not exist "frontend\node_modules" (
  echo Installing frontend packages...
  pushd frontend & call npm install & popd
)

start "Flask API (port 5000)" cmd /k ".venv\Scripts\python.exe -m backend.app"
start "Next.js UI (port 3000)" cmd /k "cd frontend && npm run dev"

echo Waiting for the servers to start...
timeout /t 8 /nobreak >nul
start "" http://localhost:3000
echo.
echo Both servers are running in their own windows. Close those windows to stop them.
