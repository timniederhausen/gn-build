@echo off
for /f "tokens=*" %%a in ('py -3 -c "import os, sys; print(os.path.dirname(sys.executable));"') do set VAR=%%a
echo %VAR%
set PATH=%VAR%;%PATH%
