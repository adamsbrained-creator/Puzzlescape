@echo off
REM Rebuilds Puzzlescape.exe from the current code in this folder.
REM Run this any time you change a .py file or anything in assets\.
REM Double-click it in Explorer, or run ".\rebuild.bat" from a terminal
REM that's already inside the src\ folder.

echo Building Puzzlescape...
echo.

"C:\Users\thead\AppData\Local\Python\pythoncore-3.13-64\python.exe" -m PyInstaller Puzzlescape.spec

echo.
echo Done. The updated app is at src\dist\Puzzlescape\Puzzlescape.exe
pause
