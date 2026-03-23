@echo off
setlocal

echo [1/3] Installing build dependency...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo Failed to install PyInstaller.
  exit /b 1
)

echo [2/3] Building onefile EXE...
pyinstaller --noconfirm --clean --onefile --windowed --name gui_editor ^
  --add-data "assets;assets" ^
  main.py
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo [3/3] Done.
echo EXE location: dist\gui_editor.exe
endlocal
