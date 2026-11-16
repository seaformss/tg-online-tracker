@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Telegram Online Tracker

set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY python --version >nul 2>nul && set "PY=python"

if not defined PY goto :nopython

if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if errorlevel 1 goto :err

if not exist ".venv\deps_ok" (
    echo Ставлю зависимости, это один раз...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :err
    echo ok> ".venv\deps_ok"
)

".venv\Scripts\python.exe" main.py
pause
exit /b

:nopython
echo Python не найден. Устанавливаю через winget...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
echo.
echo Если установка прошла успешно, закройте это окно и запустите start.bat ещё раз.
echo Если не получилось, скачайте Python с https://www.python.org/downloads/
echo и при установке поставьте галочку "Add python.exe to PATH".
pause
exit /b

:err
echo.
echo Что-то пошло не так при установке. Скопируйте текст ошибки выше.
pause
exit /b 1
