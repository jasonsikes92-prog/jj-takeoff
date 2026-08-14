@echo off
rem One-click Roberts teach loop: rebuilds the viewer, starts the local teach
rem server on http://localhost:5810 and opens it in your browser.
rem Leave this window open while you work; close it (or Ctrl+C) when done.
cd /d C:\Users\jason\JJ-Takeoff
echo Starting the Roberts virtual-takeoff teach loop...
python tools\viewer\build_viewer.py --job jobs\roberts_levelground --serve
pause
