@echo off
reg add "HKCU\Console" /v "FaceName" /t REG_SZ /d "MS Gothic" /f
echo Шрифт консоли был изменен на "MS Gothic".
pause
