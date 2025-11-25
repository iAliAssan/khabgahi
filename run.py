import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import os
import logging

# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ایمپورت توکن از فایل config
try:
    from config import API_TOKEN, SUPPORT_USERNAME
except ImportError:
    logger.error("❌ فایل config.py یافت نشد!")
    exit(1)

if not API_TOKEN or API_TOKEN == "YOUR_BOT_TOKEN_HERE":
    logger.error("❌ توکن ربات تنظیم نشده!")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)

# منطقه زمانی تهران
tehran_tz = pytz.timezone('Asia/Tehran')

# مسیر دیتابیس - استفاده از volume برای persistence
DB_PATH = '/app/data/sweep_bot.db' if os.path.exists('/app/data') else 'sweep_bot.db'

# دیتابیس
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS activities
                 (id INTEGER PRIMARY KEY, chat_id INTEGER, name TEXT, created_date TEXT, interval_hours INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS turns
                 (id INTEGER PRIMARY KEY, activity_id INTEGER, name TEXT, username TEXT, turn_date TEXT, score INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()
    logger.info("✅ دیتابیس initialized شد")

init_db()

# زمان‌بند برای چک کردن نوبت‌ها
scheduler = BackgroundScheduler(timezone=tehran_tz)

def check_and_announce_due_turns():
    """چک کردن و اعلام نوبت‌های رسیده"""
    try:
        logger.info("🔍 در حال چک کردن نوبت‌های رسیده...")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # زمان فعلی تهران
        now_tehran = get_tehran_time().strftime("%Y-%m-%d %H:%M")
        
        # پیدا کردن تمام فعالیت‌ها
        c.execute("SELECT id, chat_id, name FROM activities")
        activities = c.fetchall()
        
        announced_count = 0
        for activity_id, chat_id, activity_name in activities:
            # پیدا کردن نوبت فعلی که زمانش رسیده
            c.execute("""
                SELECT name, username, turn_date 
                FROM turns 
                WHERE activity_id = ? AND turn_date <= ? 
                ORDER BY turn_date 
                LIMIT 1
            """, (activity_id, now_tehran))
            
            due_turn = c.fetchone()
            
            if due_turn:
                name, username, turn_date = due_turn
                
                # بررسی اینکه آیا این نوبت در 10 دقیقه گذشته اعلام شده یا نه
                turn_datetime = datetime.strptime(turn_date, "%Y-%m-%d %H:%M")
                now_datetime = datetime.strptime(now_tehran, "%Y-%m-%d %H:%M")
                
                # اگر نوبت در 10 دقیقه گذشته بوده
                if (now_datetime - turn_datetime).total_seconds() <= 600:
                    text = f"🎯 نوبت {activity_name} رسیده!\n\n"
                    text += f"👤 مسئول امروز: {name} {username}\n"
                    text += f"⏰ تاریخ نوبت: {turn_date}\n\n"
                    text += "پس از انجام کار، امتیاز بدین! ⭐"
                    
                    try:
                        bot.send_message(chat_id, text, reply_markup=score_buttons(activity_id))
                        announced_count += 1
                        logger.info(f"✅ نوبت اعلام شد برای {activity_name} در چت {chat_id}")
                    except Exception as e:
                        logger.error(f"❌ خطا در ارسال پیام نوبت: {e}")
        
        conn.close()
        if announced_count > 0:
            logger.info(f"🎉 {announced_count} نوبت جدید اعلام شد")
        else:
            logger.info("✅ هیچ نوبت جدیدی برای اعلام نبود")
            
    except Exception as e:
        logger.error(f"❌ خطا در چک کردن نوبت‌ها: {e}")

# زمان‌بندی چک کردن هر 1 دقیقه
scheduler.add_job(
    check_and_announce_due_turns,
    'interval',
    minutes=1,
    id='check_due_turns'
)

# شروع scheduler
scheduler.start()
logger.info("✅ APScheduler شروع به کار کرد")

# ================================
# بقیه کدهای شما دقیقاً مانند قبل...
# (همان کدهایی که در PythonAnywhere استفاده کردید)
# ================================

# فقط این قسمت را اضافه کنید در انتهای فایل:

def main():
    """تابع اصلی برای اجرای ربات"""
    try:
        logger.info("🚀 شروع ربات مدیریت نوبت‌های گروه...")
        print("=" * 50)
        print("🤖 ربات مدیریت نوبت‌های گروه")
        print("📍 منطقه زمانی: تهران")
        print("⏰ سرویس زمان‌بندی: فعال")
        print("💾 مسیر دیتابیس: " + DB_PATH)
        print("=" * 50)
        
        # چک کردن اتصال
        bot_info = bot.get_me()
        logger.info(f"✅ ربات با موفقیت متصل شد: @{bot_info.username}")
        
        # شروع polling
        logger.info("🔄 شروع polling...")
        bot.infinity_polling()
        
    except Exception as e:
        logger.error(f"❌ خطای اصلی: {e}")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
