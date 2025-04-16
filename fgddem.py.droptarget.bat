@echo off
SET OSGEO4W_ROOT=C:\OSGeo4W
call %OSGEO4W_ROOT%\bin\o4w_env.bat

rem Python 3.x (need to check python version)
SET PYTHONHOME=%OSGEO4W_ROOT%\apps\Python312
PATH %PYTHONHOME%\Scripts;%PATH%

rem Qt 5
rem PATH %OSGEO4W_ROOT%\apps\Qt5\bin;%PATH%
rem set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\Qt5\plugins

echo on
python3 "%~dp0fgddem.py" %*

pause
