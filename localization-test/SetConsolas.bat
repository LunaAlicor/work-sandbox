@echo off
reg delete "HKCU\Console" /v "FaceName" /f
echo Шрифт консоли был возвращен к дефолтному.
pause
