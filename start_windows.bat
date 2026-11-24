@echo off
REM ClauseGuard - TRUE one-click starter for Windows.
REM Double-click this file in File Explorer: start_windows.bat
REM
REM What this does, in order:
REM   1. Creates a local Python virtual environment if one doesn't exist yet.
REM   2. Installs the required packages (first run only; needs internet once).
REM   3. Starts the local FastAPI backend and the demo website.
REM   4. Opens Chrome with the ClauseGuard extension ALREADY LOADED - no
REM      manual "Load unpacked" steps needed - using a separate, temporary
REM      Chrome profile so it never touches your normal Chrome profile/tabs
REM      and works even if you already have Chrome open elsewhere.
REM
REM No model training happens here - this expects backend\models\ to already
REM contain the pre-trained classifier (copied over from the original machine).

cd /d "%~dp0"
echo === ClauseGuard - one-click start (no Docker/Podman needed) ===

where py >nul 2>nul
if %errorlevel%==0 (
  set PYLAUNCH=py -3.11
) else (
  set PYLAUNCH=python
)

if not exist ".venv\Scripts\python.exe" (
  echo Setting up the environment for the first time, this can take a few minutes...
  %PYLAUNCH% -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip -q
  .venv\Scripts\pip.exe install -r backend\requirements.txt -q
)

if not exist "backend\models\clause_classifier.joblib" (
  echo.
  echo ERROR: backend\models\ does not contain the trained model.
  echo Copy the backend\models\ folder from the original machine - it already
  echo has minilm\, clause_classifier.joblib and model_metadata.json.
  echo Training from scratch on a low-memory laptop is not recommended.
  pause
  exit /b 1
)

echo Starting the local API (http://127.0.0.1:8000) ...
start "ClauseGuard - API" /min .venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000

echo Starting the demo website (http://127.0.0.1:5500) ...
start "ClauseGuard - Demo" /min .venv\Scripts\python.exe demo\serve_demo.py

timeout /t 6 /nobreak >nul

REM --- Find Chrome and launch it with the extension pre-loaded ---
set CHROME_EXE=
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set CHROME_EXE=%LocalAppData%\Google\Chrome\Application\chrome.exe

if "%CHROME_EXE%"=="" (
  echo.
  echo Could not find Chrome automatically. Opening the Scenario Lab in your
  echo default browser instead - you'll need to load the extension manually:
  echo   1. Open chrome://extensions  2. Enable Developer mode
  echo   3. Click "Load unpacked"  4. Select the "extension" folder
  start "" "http://127.0.0.1:5500/index.html"
  goto :done
)

echo Launching Chrome with ClauseGuard already loaded ^(separate temporary profile^) ...
start "" "%CHROME_EXE%" ^
  --user-data-dir="%TEMP%\ClauseGuardChromeProfile" ^
  --no-first-run --no-default-browser-check ^
  "http://127.0.0.1:5500/index.html"

:done
echo.
echo ClauseGuard is running.
echo   Scenario Lab: http://127.0.0.1:5500/index.html
echo   API health:   http://127.0.0.1:8000/health
echo.
echo Click the puzzle-piece/extensions icon in Chrome's toolbar and pin the
echo ClauseGuard shield icon for quick access.
echo.
echo Two minimized windows titled "ClauseGuard - API" and "ClauseGuard - Demo"
echo are now running the services. Close those windows to stop ClauseGuard.
pause
