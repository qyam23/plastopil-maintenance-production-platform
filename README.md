# Plastopil Maintenance & Production Platform — Phase 1

יישום דיווחים נייד לעובדי אקסטרוזיה באתר פלסטופיל הזורע. שלב זה כולל רק דיווח בטיחות, אחזקה ואיכות; אין Dashboard, ניהול משתמשים או תהליכי עבודה מתקדמים.

## הפעלה ב-Termux

```sh
pkg install python
cd field-report-phone-server
python -m pip install -r requirements.txt
cp .env.example .env
chmod +x run_server.sh run_tunnel.sh
./run_server.sh
```

השרת זמין ב-`http://0.0.0.0:8010`. להפעלה דרך Cloudflare Tunnel, בחלון Termux נוסף: `./run_tunnel.sh`.

## בדיקות

```sh
python tests/test_smoke.py
```

Telegram כבוי כברירת מחדל. כדי להפעיל, עדכנו את `.env` עם `TELEGRAM_ENABLED=1`, token, chat ID ו-`PUBLIC_BASE_URL`; אין לשמור את הקובץ ב-Git.

## הפעלה ב-Windows

התקינו Python 3 אם הוא עדיין אינו מותקן, ואז לחצו לחיצה כפולה על `run_server.bat`. הדפדפן ייפתח אוטומטית בכתובת `http://127.0.0.1:8010`.
