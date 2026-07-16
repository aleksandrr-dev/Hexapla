@echo off
REM Generate all narration audio. Run from repo root.
REM Each language takes many hours. Progress is printed to console.
REM Existing chapters are skipped, so it's safe to restart.

cd /d "%~dp0\.."

echo === Webster (1189 chapters) ===
python -u tools/narrate.py --lang wbt
echo Webster done.
echo.

echo === Geneva (1189 chapters) ===
python -u tools/narrate.py --lang gnv
echo Geneva done.
echo.

echo === Tyndale (451 chapters) ===
python -u tools/narrate.py --lang tyn
echo Tyndale done.
echo.

echo === Wycliffe (1189 chapters) ===
python -u tools/narrate.py --lang wyc
echo Wycliffe done.
echo.

echo All English narration complete!
pause
