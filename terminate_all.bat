@echo off
setlocal enabledelayedexpansion

echo Stopping DUBGG project processes...

:: 1. Kill by Ports (8000 for Backend, 5173 for Frontend)
echo Cleaning up ports 8000 and 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process %%a on port 8000
    taskkill /f /pid %%a
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    echo Killing process %%a on port 5173
    taskkill /f /pid %%a
)

:: 2. Kill by Name
echo Hunting for python and vite processes...
taskkill /f /im python.exe /fi "WINDOWTITLE eq api_server.py*" 2>nul
taskkill /f /im python.exe /fi "WINDOWTITLE eq app_server.py*" 2>nul
taskkill /f /im node.exe /fi "WINDOWTITLE eq vite*" 2>nul
:: Generic name matching for safety
taskkill /f /im vite.exe 2>nul

echo Cleanup complete. You can now start fresh.
pause
