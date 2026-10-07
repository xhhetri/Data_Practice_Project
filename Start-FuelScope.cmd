@echo off
REM ==========================================================================
REM  FuelScope one-click launcher for Windows 10/11.
REM  Double-click this file. It will:
REM    1. find Python 3.11-3.14 (or install Python 3.12 for your user account)
REM    2. create a private environment in .venv and install the requirements
REM    3. build the data pipeline on first run
REM    4. start the local server and open FuelScope in your browser
REM  Options (from a terminal):  Start-FuelScope.cmd --rebuild  or  --no-browser  or  --port 8800
REM ==========================================================================
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title FuelScope
pushd "%~dp0" || (echo Could not open the project folder. & pause & exit /b 1)
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "VENV_PY=.venv\Scripts\python.exe"
set "PY_INSTALL_VERSION=3.12.10"

echo.
echo  FuelScope - Australian fuel-market review
echo  ------------------------------------------
echo.

REM ---- 1. Reuse a working project environment if there is one --------------
if not exist "%VENV_PY%" goto find_python
"%VENV_PY%" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,15) else 1)" >nul 2>&1
if not errorlevel 1 goto deps
echo The existing .venv does not work on this computer; recreating it...
rmdir /s /q ".venv" >nul 2>&1

:find_python
call :locate_python
if defined PY goto make_venv

echo Python 3.11 or newer was not found on this computer.
echo FuelScope will install Python %PY_INSTALL_VERSION% for your user account only (no admin rights needed).
echo Close this window now to cancel, or
pause
call :install_python
call :locate_python
if defined PY goto make_venv
echo.
echo Python could not be installed automatically.
echo Install Python 3.12 from https://www.python.org/downloads/windows/
echo (tick "Add python.exe to PATH"), then run this file again.
goto fail

:make_venv
echo Creating the project environment with %PY% ...
%PY% -m venv ".venv"
if errorlevel 1 (
  echo Could not create the virtual environment.
  goto fail
)

REM ---- 2. Install requirements when they are missing or have changed -------
:deps
set "DEPS_STAMP=.venv\fuelscope-requirements.sha256"
set "DEPS_NEW=.venv\fuelscope-requirements.new"
"%VENV_PY%" -c "import hashlib,pathlib,sys;h=hashlib.sha256();[h.update(pathlib.Path(n).read_bytes()) for n in ('requirements-lock.txt','requirements.txt') if pathlib.Path(n).exists()];h.update(sys.version.encode());print(h.hexdigest())" > "%DEPS_NEW%" 2>nul
if not exist "%DEPS_STAMP%" goto install_deps
fc /b "%DEPS_NEW%" "%DEPS_STAMP%" >nul 2>&1
if not errorlevel 1 goto check_imports

:install_deps
echo Installing the Python packages FuelScope needs (first run: a few minutes)...
"%VENV_PY%" -m pip install --upgrade pip --quiet >nul 2>&1
"%VENV_PY%" -m pip install -r requirements-lock.txt
if errorlevel 1 (
  echo.
  echo The exact pinned versions are not available for this Python; using compatible versions instead...
  "%VENV_PY%" -m pip install -r requirements.txt
  if errorlevel 1 goto pip_failed
)
copy /y "%DEPS_NEW%" "%DEPS_STAMP%" >nul 2>&1

:check_imports
"%VENV_PY%" -c "import pandas, numpy, scipy, sklearn, statsmodels, openpyxl, pyarrow, matplotlib, sqlalchemy, dotenv" >nul 2>&1
if not errorlevel 1 goto run
echo Some packages are missing or damaged; reinstalling...
del "%DEPS_STAMP%" >nul 2>&1
"%VENV_PY%" -m pip install --force-reinstall -r requirements.txt
if errorlevel 1 goto pip_failed

REM ---- 3 + 4. Build if needed, serve, open browser ---------------------------
:run
echo.
"%VENV_PY%" launch.py %*
if errorlevel 1 goto fail
popd
endlocal
exit /b 0

:pip_failed
echo.
echo Package installation failed. Check your internet connection (or proxy) and run this file again.
goto fail

:fail
echo.
echo FuelScope did not start. Read the messages above for the reason.
pause
popd
endlocal
exit /b 1

REM ==========================================================================
REM  Subroutines
REM ==========================================================================
:locate_python
set "PY="
for %%V in (3.12 3.13 3.11 3.14) do call :try_python py -%%V
if defined PY exit /b 0
for %%D in (Python312 Python313 Python311 Python314) do call :try_python "%LOCALAPPDATA%\Programs\Python\%%D\python.exe"
if defined PY exit /b 0
for %%D in (Python312 Python313 Python311 Python314) do call :try_python "%ProgramFiles%\%%D\python.exe"
if defined PY exit /b 0
call :try_python python
if defined PY exit /b 0
call :try_python python3
exit /b 0

:try_python
if defined PY exit /b 0
%* -c "import sys, venv; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,15) else 1)" >nul 2>&1
if errorlevel 1 exit /b 0
set PY=%*
exit /b 0

:install_python
where winget >nul 2>&1
if errorlevel 1 goto install_python_download
echo Installing Python 3.12 with winget...
winget install --exact --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
call :locate_python
if defined PY exit /b 0

:install_python_download
set "PY_ARCH=amd64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "PY_ARCH=arm64"
if /i "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "PY_ARCH=arm64"
set "PY_URL=https://www.python.org/ftp/python/%PY_INSTALL_VERSION%/python-%PY_INSTALL_VERSION%-%PY_ARCH%.exe"
set "PY_SETUP=%TEMP%\fuelscope-python-%PY_INSTALL_VERSION%.exe"
echo Downloading %PY_URL% ...
curl.exe -fL --retry 3 -o "%PY_SETUP%" "%PY_URL%" >nul 2>&1
if errorlevel 1 powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing -Uri '%PY_URL%' -OutFile '%PY_SETUP%'"
if not exist "%PY_SETUP%" exit /b 1
echo Installing Python %PY_INSTALL_VERSION% for this user...
"%PY_SETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Shortcuts=0
del "%PY_SETUP%" >nul 2>&1
exit /b 0