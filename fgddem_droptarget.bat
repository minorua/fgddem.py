@echo off
SET OSGEO4W_ROOT=C:\OSGeo4W
call %OSGEO4W_ROOT%\bin\o4w_env.bat

echo on
python "%~dp0fgddem.py" %*

pause
