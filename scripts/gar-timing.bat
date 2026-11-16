@echo off
rem SPDX-License-Identifier: GPL-3.0-or-later
rem Copyright (C) 2026 Steve Prud'Homme
rem GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
setlocal
set "PYTHONPATH=%~dp0..\src;%PYTHONPATH%"
if exist "%~dp0..\.venv\Scripts\python.exe" (
  "%~dp0..\.venv\Scripts\python.exe" -m gar timing %*
) else (
  python -m gar timing %*
)
exit /b %errorlevel%
