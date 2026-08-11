@echo off
setlocal
set "BIN_DIR=%~dp0"
if exist "%BIN_DIR%..\runtime\git\cmd\git.exe" set "PATH=%BIN_DIR%..\runtime\git\cmd;%PATH%"
if exist "%BIN_DIR%..\runtime\python\python.exe" (
  "%BIN_DIR%..\runtime\python\python.exe" "%BIN_DIR%launcher.py" %*
) else (
  py -3 "%BIN_DIR%launcher.py" %*
)
exit /b %ERRORLEVEL%
