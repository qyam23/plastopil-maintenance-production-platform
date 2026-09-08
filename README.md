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

## מעבר מ־Render PostgreSQL ל־Neon

האפליקציה תומכת ב־PostgreSQL חיצוני באמצעות משתנה הסביבה `DATABASE_URL`.

1. צרו מסד נתונים ב־Neon והעתיקו את מחרוזת החיבור שלו.
2. ב־Render Dashboard, פתחו את שירות האתר והגדירו את `DATABASE_URL` כמחרוזת החיבור של Neon. אין לשמור מחרוזת זו ב־Git.
3. לשחזור העותק המקומי של הנתונים, הריצו:

```powershell
$env:DATABASE_URL = "מחרוזת-החיבור-מ־Neon"
python scripts/restore_sqlite_to_postgres.py --database-url $env:DATABASE_URL
```

4. בצעו Deploy מחדש ב־Render ובדקו יצירת דיווח, מסך ניהול וקובץ מצורף.

הערה: מסד Render שהושעה אינו זמין להעתקת מידע. כדי לשמר דיווחים שקיימים רק בו, יש לשחזר אותו זמנית באמצעות שדרוג בתשלום לפני גיבוי והעברה.

## אחסון מדיה פרטי ב־Google Drive

הקוד תומך ב־Google Drive כאחסון הראשי לתמונות, וידאו והקלטות. יש להגדיר
ב־Render, ורק שם, את משתני הסביבה `GOOGLE_DRIVE_FOLDER_ID`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` ו־`GOOGLE_REFRESH_TOKEN`.
ההרשאה הנדרשת היא `drive.file`, המוגבלת לקבצים שהאפליקציה יוצרת.
אין לשמור ערכים אלה בקוד, ב־GitHub, בקובץ `.env` משותף או ביומני מערכת.

כשכל ארבעת המשתנים מוגדרים, קובץ חדש מועלה לתיקיית Drive והמסד שומר רק
את מזהה הקובץ. בלי ההגדרה, מצב המחשב המקומי ממשיך לשמור קבצים במסד/דיסק.
