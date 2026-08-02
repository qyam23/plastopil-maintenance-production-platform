@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3 לא נמצא במחשב.
    echo יש להתקין Python 3 מ-https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set "PYTHON=python"
)

if not exist ".env" copy ".env.example" ".env" >nul
if not exist "data" mkdir "data"
if not exist "uploads\images" mkdir "uploads\images"
if not exist "uploads\videos" mkdir "uploads\videos"
if not exist "uploads\audio" mkdir "uploads\audio"

echo מתקין רכיבים נדרשים (אם טרם הותקנו)...
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ההתקנה נכשלה. בדקו שיש חיבור אינטרנט ו-Python תקין.
  pause
  exit /b 1
)

findstr /R /C:"^SECRET_KEY=." .env >nul
if errorlevel 1 (
  for /f %%s in ('%PYTHON% -c "import secrets; print(secrets.token_urlsafe(32))"') do echo SECRET_KEY=%%s>>.env
)

echo.
echo האתר פועל כעת בכתובת: http://127.0.0.1:8010
echo לסגירה: לחצו Ctrl+C בחלון זה.
start "" http://127.0.0.1:8010
%PYTHON% app.py
pause
