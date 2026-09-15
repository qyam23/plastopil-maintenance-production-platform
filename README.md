# Plastopil Maintenance & Production Platform

יישום דיווחים נייד לעובדים, עם מוקד ניהול, יומן אחזקה, דשבורד ובסיס ידע לעבודות טכנאים.

## קישורים לאפליקציה

דיווח עובד / מסך ראשי

https://plastopil-maintenance-production-platform.onrender.com/

סריקת QR

https://plastopil-maintenance-production-platform.onrender.com/scan

דיווח חדש ישיר

https://plastopil-maintenance-production-platform.onrender.com/report/new

ניהול קריאות

https://plastopil-maintenance-production-platform.onrender.com/manage

יומן אחזקה

https://plastopil-maintenance-production-platform.onrender.com/manage/journal

דשבורד אחזקה יומי

https://plastopil-maintenance-production-platform.onrender.com/manage/maintenance-dashboard

בסיס ידע — תקלות ופתרונות

https://plastopil-maintenance-production-platform.onrender.com/manage/knowledge

ניהול והדפסת QR

https://plastopil-maintenance-production-platform.onrender.com/manage/qr

התחברות מנהל / טכנאי

https://plastopil-maintenance-production-platform.onrender.com/login

תיק דיווח דיגיטלי נפתח מתוך קריאה מסוימת במסך הניהול; הכתובת שלו כוללת את מספר הקריאה (`/manage/report/<id>/case`) ולכן אינה קישור כללי קבוע. מסכי הניהול מחייבים התחברות, והדשבורד זמין למנהל בלבד.

## מסכי אחזקה חדשים

- `/manage/journal` — יומן קריאות. פתוחות תמיד לפני סגורות; סגורות נשארות בהיסטוריה.
- `/manage/maintenance-dashboard` — מדדים ממסד הנתונים לפי יום ישראלי, למנהל בלבד.
- `/manage/knowledge` — חיפוש לקחים ופתרונות שהטכנאים תיעדו.
- `/manage/report/<id>` — עבודות טכנאי, מצורפים לעבודה, שיח מקצועי פנימי ועדכונים לעובד.
- `/manage/report/<id>/case` — תיק דיווח דיגיטלי מלא, עם הדפסה/שמירה כ־PDF ורישום צפייה ואישור טיפול.

שכבת האחזקה נשמרת בטבלאות נוספות **באותו מסד נתונים** (`maintenance_actions`, `maintenance_discussion`, `maintenance_events`, `case_receipts`). לא נדרש שירות מסד נוסף בתשלום. סגירה והעברה לארכיון זמינות רק למנהל; העברה לארכיון הפיכה ואינה מוחקת נתונים. דיון פנימי אינו נשלח למדווח, בניגוד ל״עדכונים לעובד״.

הדשבורד הוא נתון מצב בכל רענון, לא סטרים בזמן אמת. לצפייה רציפה יש לרענן את העמוד. צפייה בתיק שנרשמת לאחר 3 שניות היא אישור טכני לפתיחת העמוד ולא הוכחת קריאה מלאה. קובץ PDF מציג תמונות; וידאו וקול דורשים גישה מחוברת לשרת דרך הקישורים שבתיק.

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
python tests/test_maintenance.py
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
