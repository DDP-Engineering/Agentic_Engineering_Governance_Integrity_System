@echo off & rem Probe exact Python 3.12 candidates before entering AEGIS.
setlocal
set "BIN_DIR=%~dp0"
if exist "%BIN_DIR%..\runtime\git\cmd\git.exe" set "PATH=%BIN_DIR%..\runtime\git\cmd;%PATH%"
if not exist "%BIN_DIR%..\runtime\python\python.exe" goto probe_external_python
"%BIN_DIR%..\runtime\python\python.exe" "%BIN_DIR%launcher.py" %*
exit /b %ERRORLEVEL%

:probe_external_python
for /f "tokens=1-3 delims=. " %%A in ('python3.12 --version 2^>^&1') do if "%%A.%%B.%%C"=="Python.3.12" goto use_python312
for /f "tokens=1-3 delims=. " %%A in ('py -3.12 --version 2^>^&1') do if "%%A.%%B.%%C"=="Python.3.12" goto use_py312
for /f "tokens=1-3 delims=. " %%A in ('python3 --version 2^>^&1') do if "%%A.%%B.%%C"=="Python.3.12" goto use_python3
for /f "tokens=1-3 delims=. " %%A in ('python --version 2^>^&1') do if "%%A.%%B.%%C"=="Python.3.12" goto use_python
goto missing_python

:use_python312
python3.12 "%BIN_DIR%launcher.py" %*
exit /b %ERRORLEVEL%

:use_py312
py -3.12 "%BIN_DIR%launcher.py" %*
exit /b %ERRORLEVEL%

:use_python3
python3 "%BIN_DIR%launcher.py" %*
exit /b %ERRORLEVEL%

:use_python
python "%BIN_DIR%launcher.py" %*
exit /b %ERRORLEVEL%

:missing_python
if "%~1"=="" goto emit_missing_python_human
if /i "%~1"=="--format=json" goto emit_missing_python_json
if /i "%~1"=="--format" goto inspect_format_value
shift
goto missing_python

:inspect_format_value
shift
if /i "%~1"=="json" goto emit_missing_python_json
goto missing_python

:emit_missing_python_json
echo {"schema":"aegis.machine.response","schema_version":1,"product":"AEGIS","product_version":"1.0.0","operation":"launcher.start","operation_id":"OP-00000000000000000000000000000000","operation_status":"error","run_id":null,"stage":null,"revision":null,"outcome":null,"message":"AEGIS requires Python 3.12 on PATH.","data":{},"findings":[],"artifacts":[],"next_actions":[],"error":{"code":"missing_prerequisite","summary":"AEGIS requires Python 3.12 on PATH.","field":null,"path":null,"retryable":false,"details":{}},"truncated":false,"details_ref":null}
exit /b 5

:emit_missing_python_human
echo AEGIS requires Python 3.12 on PATH.
echo Operation: launcher.start
echo Status: error
echo Product: AEGIS 1.0.0
echo Error: missing_prerequisite: AEGIS requires Python 3.12 on PATH.
exit /b 5
