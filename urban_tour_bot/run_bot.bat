@echo off
set "PROJ=C:\Users\Лиза\Downloads\Проект ИИ контроль показателей\urban_tour_bot"
cd /d "%PROJ%"
if not exist "%PROJ%\logs" mkdir "%PROJ%\logs"
"%PROJ%\.venv\Scripts\python.exe" "%PROJ%\bot.py" >> "%PROJ%\logs\stdout.log" 2>> "%PROJ%\logs\stderr.log"
