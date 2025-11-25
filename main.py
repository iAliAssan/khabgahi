import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import pytz

# ایمپورت توکن از فایل config
try:
    from config import API_TOKEN, SUPPORT_USERNAME
except ImportError:
    print("❌ فایل config.py یافت نشد!")
    exit(1)

if not API_TOKEN or API_TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("❌ توکن ربات تنظیم نشده!")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)

# منطقه زمانی تهران
tehran_tz = pytz.timezone('Asia/Tehran')
DB_PATH = '/app/data/sweep_bot.db' if os.path.exists('/app/data') else 'sweep_bot.db'
# دیتابیس
def init_db():
    conn = sqlite3.connect('sweep_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS activities
                 (id INTEGER PRIMARY KEY, chat_id INTEGER, name TEXT, created_date TEXT, interval_hours INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS turns
                 (id INTEGER PRIMARY KEY, activity_id INTEGER, name TEXT, username TEXT, turn_date TEXT, score INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# ================================
# بخش خصوصی (Private Chat)
# ================================

def private_chat_menu():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✨ اضافه کردن به گروه", url="https://t.me/khabgahi_bot?startgroup=true")
    )
    markup.row(
        types.InlineKeyboardButton("📚 راهنمای جامع", callback_data="help"),
        types.InlineKeyboardButton("💌 پشتیبانی", callback_data="support")
    )
    return markup

# دستور start در چت خصوصی
@bot.message_handler(commands=['start'], chat_types=['private'])
def send_private_welcome(message):
    text = (
        "💡 سیستم مدیریت نوبت گروه\n\n"
        "فعالیت‌های گروهت رو سیستماتیک مدیریت کن\n"
        "از تنظیم نوبت تا ثبت امتیاز! 📈\n\n"
        "خدمت مورد نظرتون چیه؟"
    )
    bot.send_message(message.chat.id, text, reply_markup=private_chat_menu())

# مدیریت کلیک در چت خصوصی
@bot.callback_query_handler(func=lambda call: call.message.chat.type == 'private')
def handle_private_callback(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == "help":
        show_help(chat_id, message_id)
    elif call.data == "support":
        show_support(chat_id, message_id)
    elif call.data == "back_to_private_menu":
        show_private_menu(chat_id, message_id)

def show_private_menu(chat_id, message_id):
    text = "🏠 منوی اصلی\n\nدوباره سلام! 😄 چیکار می‌تونم برات انجام بدم؟"
    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=private_chat_menu()
    )

def show_help(chat_id, message_id):
    text = (
        "📚 راهنمای جامع ربات:\n\n"

        "🎯 نحوه اضافه کردن به گروه:\n"
        "1. روی دکمه 'اضافه کردن به گروه' کلیک کن\n"
        "2. گروه مورد نظرت رو انتخاب کن\n"
        "3. ربات رو مثل یه سلبریتی به گروه اضافه کن! 🌟\n\n"

        "🚀 بعد از اضافه کردن به گروه:\n"
        "1. ادمین گروه باید دسترسی 'ارسال پیام' رو به ربات بده\n"
        "2. با دستور /start ربات رو در گروه فعال کن\n"
        "3. از منوی ربات برای تنظیم فعالیت‌ها استفاده کن\n\n"

        "💎 امکانات فوق‌العاده ربات در گروه:\n"
        "• مدیریت نوبت‌های چرخشی برای فعالیت‌های مختلف 🔄\n"
        "• سیستم امتیازدهی به افراد 🏆\n"
        "• نمایش نوبت‌های آینده 📅\n"
        "• جدول امتیازات 📊\n"
        "• پشتیبانی از چندین فعالیت همزمان 🎪\n\n"

        "💡 نکته طلایی: فقط ادمین‌های گروه می‌تونن فعالیت‌ها رو تنظیم کنن! 👑"
    )

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_private_menu"))

    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

def show_support(chat_id, message_id):
    text = (
        f"💌 پشتیبانی\n\n"
        f"اگر مشکلی داری، انتقاد یا پیشنهادی داری، ما اینجاییم برات! 🤝\n\n"
        f"👤 {SUPPORT_USERNAME}\n\n"
        f"سعی می‌کنیم در سریع‌ترین زمان ممکن پاسختو بدیم! ⚡"
    )

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_private_menu"))

    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

# ================================
# بخش گروه (Group Chat)
# ================================

# بررسی دسترسی ادمین
def is_admin(chat_id, user_id):
    try:
        # اگر چت خصوصی باشد، کاربر ادمین است
        if chat_id > 0:
            return True

        # در گروه، بررسی وضعیت کاربر
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        print(f"خطا در بررسی ادمین: {e}")
        return False

# دکمه‌های شیشه‌ای منوی اصلی در گروه
def group_main_menu(chat_id, user_id):
    markup = types.InlineKeyboardMarkup()

    # فقط ادمین می‌تواند تنظیمات را ببیند
    if is_admin(chat_id, user_id):
        markup.row(
            types.InlineKeyboardButton("⚡ تنظیم فعالیت جدید", callback_data="setup_activity")
        )

    markup.row(
        types.InlineKeyboardButton("📅 نوبت‌های آینده", callback_data="next_turn"),
        types.InlineKeyboardButton("🏆 جدول امتیازات", callback_data="show_scores")
    )

    # فقط ادمین می‌تواند فعالیت‌ها را مدیریت کند
    if is_admin(chat_id, user_id):
        markup.row(
            types.InlineKeyboardButton("🎛️ مدیریت فعالیت‌ها", callback_data="manage_activities")
        )

    return markup

# منوی انتخاب فعالیت
def activities_menu(chat_id, user_id):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✨ تمیزکاری", callback_data="activity_تمیزکاری"),
        types.InlineKeyboardButton("👨‍🍳 پخت غذا", callback_data="activity_پخت غذا")
    )
    markup.row(
        types.InlineKeyboardButton("📦 خرید مواد غذایی", callback_data="activity_خرید مواد غذایی"),
        types.InlineKeyboardButton("🧽 شستشوی ظروف", callback_data="activity_شستشوی ظروف")
    )
    markup.row(types.InlineKeyboardButton("✨ فعالیت دلخواه", callback_data="custom_activity"))
    markup.row(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
    return markup

# منوی مدیریت فعالیت‌ها - نسخه جدید با دسته‌بندی مرتب‌تر
def manage_activities_menu(chat_id, user_id):
    activities = get_all_activities(chat_id)
    markup = types.InlineKeyboardMarkup()

    if activities:
        markup.row(types.InlineKeyboardButton("🗑️ حذف فعالیت‌ها", callback_data="delete_activities"))
        markup.row(types.InlineKeyboardButton("⏰ ویرایش فواصل", callback_data="edit_intervals"))
    else:
        markup.row(types.InlineKeyboardButton("📝 هیچ فعالیتی وجود ندارد", callback_data="none"))

    markup.row(types.InlineKeyboardButton("✨ ایجاد فعالیت جدید", callback_data="setup_activity"))
    markup.row(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main"))
    return markup

# منوی حذف فعالیت‌ها - جدید
def delete_activities_menu(chat_id, user_id):
    activities = get_all_activities(chat_id)
    markup = types.InlineKeyboardMarkup()

    if activities:
        for activity in activities:
            markup.row(
                types.InlineKeyboardButton(f"🗑️ حذف {activity['name']}", callback_data=f"delete_activity_{activity['id']}")
            )
    else:
        markup.row(types.InlineKeyboardButton("📝 هیچ فعالیتی وجود ندارد", callback_data="none"))

    markup.row(types.InlineKeyboardButton("🔙 بازگشت", callback_data="manage_activities"))
    return markup

# منوی ویرایش فواصل
def edit_intervals_menu(chat_id, user_id):
    activities = get_all_activities(chat_id)
    markup = types.InlineKeyboardMarkup()

    if activities:
        for activity in activities:
            markup.row(
                types.InlineKeyboardButton(f"⏰ {activity['name']}", callback_data=f"edit_interval_{activity['id']}")
            )
    else:
        markup.row(types.InlineKeyboardButton("📝 هیچ فعالیتی وجود ندارد", callback_data="none"))

    markup.row(types.InlineKeyboardButton("🔙 بازگشت", callback_data="manage_activities"))
    return markup

# دکمه‌های امتیازدهی با activity_id
def score_buttons(activity_id):
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("👎 -1", callback_data=f"score_-1_{activity_id}"),
        types.InlineKeyboardButton("😐 0", callback_data=f"score_0_{activity_id}"),
        types.InlineKeyboardButton("👍 +1", callback_data=f"score_1_{activity_id}")
    )
    return markup

# دکمه بازگشت برای گروه
def group_back_button(chat_id, user_id):
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main"))
    return markup

# دریافت زمان فعلی تهران
def get_tehran_time():
    return datetime.now(tehran_tz)

# دستور start در گروه
@bot.message_handler(commands=['start'], chat_types=['group', 'supergroup'])
def send_group_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = "🎉 ربات مدیریت نوبت‌های گروه فعال شد!\n\nحالا می‌تونیم مثل یه تیم حرفه‌ای همه کارها رو مدیریت کنیم! 💪✨"
    bot.send_message(chat_id, text, reply_markup=group_main_menu(chat_id, user_id))

# مدیریت کلیک در گروه
@bot.callback_query_handler(func=lambda call: call.message.chat.type in ['group', 'supergroup'])
def handle_group_callback(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id

    if call.data == "setup_activity":
        if is_admin(chat_id, user_id):
            show_activities_menu(chat_id, message_id, user_id)
        else:
            bot.answer_callback_query(call.id, "❌ فقط ادمین‌ها می‌تونن این کار رو انجام بدن! 👮‍♂️")
    elif call.data == "manage_activities":
        if is_admin(chat_id, user_id):
            show_manage_activities(chat_id, message_id, user_id)
        else:
            bot.answer_callback_query(call.id, "❌ فقط ادمین‌ها می‌تونن این کار رو انجام بدن! 👮‍♂️")
    elif call.data == "delete_activities":  # حالت جدید برای منوی حذف
        if is_admin(chat_id, user_id):
            show_delete_activities(chat_id, message_id, user_id)
        else:
            bot.answer_callback_query(call.id, "❌ فقط ادمین‌ها می‌تونن این کار رو انجام بدن! 👮‍♂️")
    elif call.data == "next_turn":
        show_next_turns(chat_id, message_id, user_id)
    elif call.data == "show_scores":
        show_scores(chat_id, message_id, user_id)
    elif call.data.startswith('score_'):
        handle_score(call, chat_id, message_id, user_id)
    elif call.data == "back_to_main":
        show_group_main_menu(chat_id, message_id, user_id)
    elif call.data.startswith('activity_'):
        activity_name = call.data.replace('activity_', '')
        ask_for_user_list(chat_id, message_id, user_id, activity_name)
    elif call.data == "custom_activity":
        ask_for_custom_activity(chat_id, message_id, user_id)
    elif call.data.startswith('delete_activity_'):
        if is_admin(chat_id, user_id):
            activity_id = int(call.data.replace('delete_activity_', ''))
            confirm_delete_activity(chat_id, message_id, user_id, activity_id)
        else:
            bot.answer_callback_query(call.id, "❌ فقط ادمین‌ها می‌تونن این کار رو انجام بدن! 👮‍♂️")
    elif call.data.startswith('confirm_delete_activity_'):
        if is_admin(chat_id, user_id):
            activity_id = int(call.data.replace('confirm_delete_activity_', ''))
            delete_activity(chat_id, message_id, user_id, activity_id)
        else:
            bot.answer_callback_query(call.id, "❌ فقط ادمین‌ها می‌تونن این کار رو انجام بدن! 👮‍♂️")
    elif call.data == "cancel_delete_activity":
        show_delete_activities(chat_id, message_id, user_id)
    elif call.data == "edit_intervals":
        show_edit_intervals_menu(chat_id, message_id, user_id)
    elif call.data.startswith('edit_interval_'):
        if is_admin(chat_id, user_id):
            activity_id = int(call.data.replace('edit_interval_', ''))
            ask_for_new_interval(chat_id, message_id, user_id, activity_id)
        else:
            bot.answer_callback_query(call.id, "❌ فقط ادمین‌ها می‌تونن این کار رو انجام بدن! 👮‍♂️")
    elif call.data.startswith('confirm_turns_'):
        handle_confirm_turns(call)
    elif call.data == "edit_turns":
        handle_edit_turns(call)

def show_activities_menu(chat_id, message_id, user_id):
    text = (
        "📋 انتخاب نوع فعالیت\n\n"
        "از پیشنهادهای ما استفاده کن\n"
        "یا فعالیت دلخواهت رو ایجاد کن! ✨"
    )
    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=activities_menu(chat_id, user_id)
    )

def show_group_main_menu(chat_id, message_id, user_id):
    text = "🏠 منوی اصلی\n\nسلام قهرمان! 😎 چیکار می‌تونم برات انجام بدم؟"
    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=group_main_menu(chat_id, user_id)
    )

def show_manage_activities(chat_id, message_id, user_id):
    activities = get_all_activities(chat_id)

    if activities:
        text = "🎛️ مدیریت فعالیت‌ها\n\n"
        text += f"📊 تعداد فعالیت‌ها: {len(activities)}\n\n"
        text += "فعالیت‌های موجود:\n\n"
        for activity in activities:
            text += f"• {activity['name']}\n"
        text += "\nمی‌تونی فعالیت‌ها رو حذف کنی، فواصل نوبت‌ها رو تغییر بدی یا فعالیت جدید ایجاد کنی ✨"
    else:
        text = "🎛️ مدیریت فعالیت‌ها\n\nهنوز هیچ فعالیتی ایجاد نکردی!\n\nبیا اولین فعالیت رو مثل یه حرفه‌ای ایجاد کنیم! 🚀"

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=manage_activities_menu(chat_id, user_id)
    )

# تابع جدید برای نمایش منوی حذف فعالیت‌ها
def show_delete_activities(chat_id, message_id, user_id):
    activities = get_all_activities(chat_id)

    if activities:
        text = "🗑️ حذف فعالیت‌ها\n\n"
        text += "کدام فعالیت رو می‌خوای حذف کنی؟\n\n"
        for activity in activities:
            text += f"• {activity['name']}\n"
        text += "\n⚠️ با حذف فعالیت، تمام نوبت‌ها و امتیازات مربوطه پاک میشن!"
    else:
        text = "🗑️ حذف فعالیت‌ها\n\nهنوز هیچ فعالیتی برای حذف وجود نداره!\n\nبیا اولین فعالیت رو ایجاد کنیم! 🚀"

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=delete_activities_menu(chat_id, user_id)
    )

def show_edit_intervals_menu(chat_id, message_id, user_id):
    activities = get_all_activities(chat_id)

    if activities:
        text = "⏰ ویرایش فواصل نوبت‌ها\n\n"
        text += "لطفاً فعالیتی که می‌خوای فاصله نوبت‌هاش رو تغییر بدی انتخاب کن:\n\n"
        for activity in activities:
            text += f"• {activity['name']}\n"
    else:
        text = "⏰ ویرایش فواصل نوبت‌ها\n\nهنوز هیچ فعالیتی ایجاد نکردی!\n\nبیا اولین فعالیت رو ایجاد کنیم! 🚀"

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=edit_intervals_menu(chat_id, user_id)
    )

def ask_for_custom_activity(chat_id, message_id, user_id):
    text = "✨ نام فعالیت دلخواهت رو وارد کن:\n\nمثلاً: ورزش، مطالعه، بازی و... \nهر چیزی که دوست داری! 🎨"

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔙 بازگشت", callback_data="setup_activity"))

    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, process_custom_activity, message_id, user_id)

def process_custom_activity(message, original_message_id, user_id):
    activity_name = message.text.strip()
    if activity_name:
        # حذف پیام ارسالی کاربر
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

        ask_for_user_list(message.chat.id, original_message_id, user_id, activity_name)
    else:
        text = "❌ نام فعالیت نمی‌تونه خالی باشه!\n\nبیا دوباره تلاش کنیم؟ 🤗"
        bot.edit_message_text(
            text,
            message.chat.id,
            original_message_id,
            reply_markup=activities_menu(message.chat.id, user_id)
        )

# دریافت لیست افراد - نسخه جدید
def ask_for_user_list(chat_id, message_id, user_id, activity_name):
    text = (
        f"👥 بیا برای فعالیت *{activity_name}* دوستات رو اضافه کنیم! 🎉\n\n"
        "اسم و یوزرنیم دوستات رو به یکی از فرمت‌های زیر برام بفرست:\n\n"
        "🎯 **فرمت تکنفره (هر نفر در یک خط):**\n"
        "```\n"
        "علی @username1\n"
        "پرنیا @username2\n"
        "همایون @username3\n"
        "```\n\n"
        "👥 **فرمت چندنفره (هر خط = یک نوبت گروهی):**\n"
        "```\n"
        "آرمان و کاوه @username1 @username2\n"
        "سپهر و بهمن @username3 @username4\n"
        "آتوسا و پرنیا @username5 @username6\n"
        "```\n\n"
        "📌 **نکته مهم:** \n"
        "هر خط = یک نوبت جداگانه\n"
        "اگر می‌خوای چند نفر با هم تو یه نوبت کار کنن، همشون رو توی یک خط بنویس\n\n"
        "📨 برای ارسال، این پیام رو ریپلای کن\n"
        "🔍 فقط با ریپلای قادر به خواندن پیامت هستم"
    )

    markup = group_back_button(chat_id, user_id)
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler_by_chat_id(chat_id, process_user_list, message_id, user_id, activity_name)

def process_user_list(message, original_message_id, user_id, activity_name):
    try:
        # حذف پیام لیست ارسالی کاربر
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

        lines = message.text.strip().split('\n')
        turns = []  # لیست نوبت‌ها

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # جدا کردن نام‌ها و یوزرنیم‌ها
            parts = line.split('@')

            # بخش نام‌ها (قبل از اولین @)
            names_part = parts[0].strip()

            # بخش یوزرنیم‌ها (همه قسمت‌های بعد از اولین @)
            usernames = []
            for i in range(1, len(parts)):
                username = '@' + parts[i].split()[0] if parts[i].split() else ''
                if username and username != '@':
                    usernames.append(username)

            # پردازش نام‌ها (ممکنه چند نام با "و" جدا شده باشند)
            names = []
            if ' و ' in names_part:
                # حالت چند نفره
                name_parts = names_part.split(' و ')
                for name in name_parts:
                    if name.strip():
                        names.append(name.strip())
            else:
                # حالت تکنفره
                if names_part.strip():
                    names.append(names_part.strip())

            # ایجاد نوبت
            if names and usernames:
                turn = {
                    'names': names,
                    'usernames': usernames
                }
                turns.append(turn)

        if turns:
            # نمایش پیش‌نمایش و درخواست تأیید
            show_turns_preview(message.chat.id, original_message_id, user_id, activity_name, turns)
        else:
            text = "❌ اوه! فرمت لیست درست نیست!\n\nبیا دوباره تلاش کنیم؟ 🤗"
            bot.edit_message_text(
                text,
                message.chat.id,
                original_message_id,
                reply_markup=group_main_menu(message.chat.id, user_id)
            )

    except Exception as e:
        print(f"خطا در پردازش لیست: {e}")
        text = "❌ یه مشکلی پیش اومد!\n\nبیا از اول شروع کنیم؟ 🫠"
        bot.edit_message_text(
            text,
            message.chat.id,
            original_message_id,
            reply_markup=group_main_menu(message.chat.id, user_id)
        )

def show_turns_preview(chat_id, message_id, user_id, activity_name, turns):
    text = f"🎯 **پیش‌نمایش نوبت‌های {activity_name}:**\n\n"

    for i, turn in enumerate(turns, 1):
        text += f"**نوبت {i}:**\n"

        if len(turn['names']) == 1:
            # حالت تکنفره
            text += f"👤 {turn['names'][0]} {turn['usernames'][0] if turn['usernames'] else ''}\n"
        else:
            # حالت چند نفره
            names_text = " و ".join(turn['names'])
            usernames_text = " ".join(turn['usernames'])
            text += f"👥 {names_text} {usernames_text}\n"

        text += "\n"

    text += "✅ آیا این نوبت‌ها درست هستند؟"

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ بله، درسته", callback_data=f"confirm_turns_{activity_name}"),
        types.InlineKeyboardButton("❌ نه، ویرایش کن", callback_data="edit_turns")
    )

    # ذخیره موقت نوبت‌ها برای استفاده بعدی
    save_temp_turns(chat_id, turns)

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

# تابع برای ذخیره موقت نوبت‌ها
def save_temp_turns(chat_id, turns):
    # استفاده از یک دیکشنری ساده برای ذخیره موقت
    if not hasattr(bot, 'temp_data'):
        bot.temp_data = {}
    bot.temp_data[chat_id] = turns

# تابع برای بازیابی نوبت‌های موقت
def get_temp_turns(chat_id):
    if hasattr(bot, 'temp_data'):
        return bot.temp_data.get(chat_id, [])
    return []

# مدیریت تأیید نوبت‌ها
def handle_confirm_turns(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id

    activity_name = call.data.replace('confirm_turns_', '')
    turns = get_temp_turns(chat_id)

    if turns:
        # ذخیره فعالیت و سپس پرسیدن فاصله نوبت‌ها
        ask_for_interval(chat_id, message_id, turns, user_id, activity_name)
    else:
        bot.answer_callback_query(call.id, "❌ اطلاعات نوبت‌ها پیدا نشد!")

def handle_edit_turns(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id

    # بازگشت به مرحله قبل
    text = "🔧 بیا دوباره لیست اسامی رو وارد کنیم!\n\nفرمت‌های قابل قبول:\n\n• تکنفره:\nعلی @username1\n\n• چندنفره:\nآرمان و کاوه @username1 @username2"

    markup = group_back_button(chat_id, user_id)
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

def ask_for_interval(chat_id, message_id, turns, user_id, activity_name):
    text = (
        f"⏰ حالا برای فعالیت {activity_name} نوبت تنظیم زمان‌هاست! 🎯\n\n"
        "فاصله بین نوبت‌ها رو به ساعت وارد کن:\n\n"
        "📝 مثال‌ها:\n"
        "• 168 ساعت = 7 روز 🗓️\n"
        "• 24 ساعت = 1 روز ☀️\n"
        "• 48 ساعت = 2 روز 🌟\n\n"
        "منتظر عدد تو هستم... ⏳"
    )

    markup = group_back_button(chat_id, user_id)
    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

    # ذخیره activity_name در دیتای موقت برای استفاده در مرحله بعد
    if not hasattr(bot, 'temp_activity_data'):
        bot.temp_activity_data = {}
    bot.temp_activity_data[chat_id] = {
        'turns': turns,
        'activity_name': activity_name
    }

    bot.register_next_step_handler_by_chat_id(chat_id, process_interval, message_id, user_id)

def process_interval(message, original_message_id, user_id):
    try:
        interval_hours = int(message.text)

        # حذف پیام interval ارسالی کاربر
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

        # بازیابی دیتای موقت
        if hasattr(bot, 'temp_activity_data'):
            temp_data = bot.temp_activity_data.get(message.chat.id, {})
            turns = temp_data.get('turns', [])
            activity_name = temp_data.get('activity_name', '')

            if turns:
                # ذخیره فعالیت و کاربران
                activity_id = save_activity(message.chat.id, activity_name, interval_hours)
                save_users_new(turns, interval_hours, activity_id)

                text = f"🎉 عالی بود! کارت حرفه‌ای بود! \n\n✅ فعالیت {activity_name} با {len(turns)} نوبت ذخیره شد\n⏰ فاصله نوبت‌ها: {interval_hours} ساعت\n\nحالا بریم سراغ نوبت‌ها! 🚀"

                bot.edit_message_text(
                    text,
                    message.chat.id,
                    original_message_id,
                    reply_markup=group_main_menu(message.chat.id, user_id)
                )

                # اعلام اولین نوبت در پیام جدید
                announce_next_turn(message.chat.id, activity_id)
            else:
                raise Exception("دیتای موقت پیدا نشد")
        else:
            raise Exception("دیتای موقت پیدا نشد")

    except ValueError:
        text = "❌ اوه! این عدد معتبر نیست!\n\nلطفاً یک عدد وارد کن مثلاً 24 یا 168 🤗"
        bot.edit_message_text(
            text,
            message.chat.id,
            original_message_id,
            reply_markup=group_main_menu(message.chat.id, user_id)
        )
    except Exception as e:
        print(f"خطا در پردازش فاصله: {e}")
        text = "❌ یه مشکلی پیش اومد!\n\nبیا از اول شروع کنیم؟ 🫠"
        bot.edit_message_text(
            text,
            message.chat.id,
            original_message_id,
            reply_markup=group_main_menu(message.chat.id, user_id)
        )

# تابع جدید برای ذخیره کاربران با فرمت جدید
def save_users_new(turns, interval_hours, activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()

    # حذف نوبت‌های قبلی این فعالیت
    c.execute("DELETE FROM turns WHERE activity_id = ?", (activity_id,))

    now = get_tehran_time()
    for i, turn in enumerate(turns):
        turn_date = now + timedelta(hours=i * interval_hours)

        # برای هر نوبت، همه افراد آن نوبت را ذخیره می‌کنیم
        for j, (name, username) in enumerate(zip(turn['names'], turn['usernames'])):
            c.execute("INSERT INTO turns (activity_id, name, username, turn_date, score) VALUES (?, ?, ?, ?, 0)",
                     (activity_id, name, username, turn_date.strftime("%Y-%m-%d %H:%M")))

    conn.commit()
    conn.close()

def ask_for_new_interval(chat_id, message_id, user_id, activity_id):
    activity_name = get_activity_name(activity_id)
    text = (
        f"⏰ ویرایش فاصله نوبت‌های {activity_name}\n\n"
        "فاصله جدید بین نوبت‌ها رو به ساعت وارد کن:\n\n"
        "📝 مثال‌ها:\n"
        "• 168 ساعت = 7 روز 🗓️\n"
        "• 24 ساعت = 1 روز ☀️\n"
        "• 48 ساعت = 2 روز 🌟\n\n"
        "منتظر عدد تو هستم... ⏳"
    )

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔙 بازگشت", callback_data="edit_intervals"))

    bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, process_new_interval, message_id, user_id, activity_id)

def process_new_interval(message, original_message_id, user_id, activity_id):
    try:
        interval_hours = int(message.text)

        # حذف پیام interval ارسالی کاربر
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

        # به‌روزرسانی فواصل نوبت‌ها
        update_turn_intervals(activity_id, interval_hours)

        activity_name = get_activity_name(activity_id)
        text = f"✅ فاصله نوبت‌های {activity_name} با موفقیت به {interval_hours} ساعت تغییر کرد!\n\nحالا نوبت‌ها با فاصله جدید محاسله میشن 🎯"

        bot.edit_message_text(
            text,
            message.chat.id,
            original_message_id,
            reply_markup=manage_activities_menu(message.chat.id, user_id)
        )

    except ValueError:
        text = "❌ اوه! این عدد معتبر نیست!\n\nلطفاً یک عدد وارد کن مثلاً 24 یا 168 🤗"
        bot.edit_message_text(
            text,
            message.chat.id,
            original_message_id,
            reply_markup=manage_activities_menu(message.chat.id, user_id)
        )

def confirm_delete_activity(chat_id, message_id, user_id, activity_id):
    activity_name = get_activity_name(activity_id)
    text = f"⚠️ آیا مطمئنی می‌خوای فعالیت {activity_name} رو حذف کنی؟\n\nاین عمل همه نوبت‌ها و امتیازات این فعالیت رو پاک می‌کنه! 🗑️"

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"confirm_delete_activity_{activity_id}"),
        types.InlineKeyboardButton("❌ نه، انصراف", callback_data="cancel_delete_activity")
    )

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=markup
    )

def delete_activity(chat_id, message_id, user_id, activity_id):
    activity_name = get_activity_name(activity_id)

    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    c.execute("DELETE FROM turns WHERE activity_id = ?", (activity_id,))
    conn.commit()
    conn.close()

    text = f"✅ فعالیت {activity_name} با موفقیت حذف شد!\n\nمی‌تونی فعالیت جدیدی ایجاد کنی یا فعالیت‌های دیگه رو مدیریت کنی ✨"

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=delete_activities_menu(chat_id, user_id)
    )

# اعلام نوبت در پیام جدید
def announce_next_turn(chat_id, activity_id):
    next_turn = get_current_turn(activity_id)
    if next_turn:
        activity_name = get_activity_name(activity_id)
        text = f"🎯 نوبت {activity_name} رسیده!\n\n"
        text += f"👤 مسئول امروز: {next_turn['name']} {next_turn['username']}\n"
        text += f"⏰ تاریخ نوبت: {next_turn['turn_date']}\n\n"
        text += "پس از انجام کار، امتیاز بدین! ⭐"

        bot.send_message(chat_id, text, reply_markup=score_buttons(activity_id))

# نمایش نوبت‌های آینده با فرمت جدید
def show_next_turns(chat_id, message_id, user_id):
    activities = get_all_activities(chat_id)

    if not activities:
        text = "*🎯 هنوز فعالیتی تنظیم نکردی!*\n\n*بیا از اول شروع کنیم و یه فعالیت جدید ایجاد کنیم؟* 🌟"
    else:
        text = "*📅 نوبت‌های آینده همه فعالیت‌ها:*\n\n"

        all_turns = []
        for activity in activities:
            turns = get_next_turns(3, activity['id'])
            activity_name = get_activity_name(activity['id'])

            for turn in turns:
                turn['activity_name'] = activity_name
                all_turns.append(turn)

        all_turns.sort(key=lambda x: x['turn_date'])

        if not all_turns:
            text += "*📭 هیچ نوبت آینده‌ای وجود نداره!*\n"
        else:
            for i, turn in enumerate(all_turns[:5], 1):
                # انتخاب ایموجی خط جداکننده بر اساس شماره نوبت
                if i == 1:
                    line_emoji = "🏃"
                elif i == 2:
                    line_emoji = "🚶"
                elif i == 3:
                    line_emoji = "🪑"
                else:
                    line_emoji = "📋"

                # انتخاب ایموجی نوبت
                if i == 1:
                    turn_emoji = "🎯"
                elif i == 2:
                    turn_emoji = "⏳"
                else:
                    turn_emoji = "📋"

                text += f"*{line_emoji}┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅*\n"
                text += f"*{turn_emoji} نوبت {i}*\n"
                text += f"*👤:* *{turn['name']}* *{turn['username']}*\n"
                text += f"*⏰:* *{turn['turn_date']}*\n"
                text += f"*🎯:* *{turn['activity_name']}*\n\n"

        text += "*همه با هم کارها رو مثل یه تیم قوی انجام میدیم!* 💪"

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=group_main_menu(chat_id, user_id),
        parse_mode='Markdown'
    )

# نمایش امتیازات همه فعالیت‌ها
def show_scores(chat_id, message_id, user_id):
    activities = get_all_activities(chat_id)

    if not activities:
        text = "📊 هنوز فعالیتی برای نمایش امتیازات وجود نداره!\n\nبیا یه فعالیت جدید ایجاد کنیم؟ 🌟"
    else:
        text = "🏆 جدول امتیازات\n\n"
        for activity in activities:
            scores = get_scores(activity['id'])
            activity_name = get_activity_name(activity['id'])

            if not scores:
                text += f"📊 برای فعالیت {activity_name} هنوز امتیازی ثبت نشده!\n\n"
            else:
                text += f"🎯 {activity_name}:\n"
                for i, score in enumerate(scores, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔸"
                    text += f"{medal} {score['name']}: {score['score']} امتیاز\n"
                text += "\n"

        text += "بنظرت برنده این دور کیه؟! 🎊"

    bot.edit_message_text(
        text,
        chat_id,
        message_id,
        reply_markup=group_main_menu(chat_id, user_id)
    )

# مدیریت امتیازدهی - نسخه اصلاح شده
def handle_score(call, chat_id, message_id, user_id):
    # جدا کردن score و activity_id از callback_data
    data_parts = call.data.split('_')
    score = int(data_parts[1])
    activity_id = int(data_parts[2])

    # ثبت امتیاز برای نوبت جاری
    current_turn = get_current_turn(activity_id)
    if current_turn:
        update_score(current_turn['name'], score, activity_id)

        # حرکت به نوبت بعدی (سیستم چرخشی)
        move_to_next_turn(current_turn['name'], activity_id)

        # حذف پیام نوبت جاری
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass

        # اعلام نوبت بعدی در پیام جدید
        announce_next_turn(chat_id, activity_id)

        # پاسخ به کاربر
        bot.answer_callback_query(call.id, f"✅ امتیاز {score} ثبت شد! 🎯")
    else:
        bot.answer_callback_query(call.id, "❌ نوبتی برای امتیازدهی وجود نداره! 🤷‍♂️")

# ================================
# توابع دیتابیس
# ================================

def save_activity(chat_id, activity_name, interval_hours):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()
    now = get_tehran_time().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO activities (chat_id, name, created_date, interval_hours) VALUES (?, ?, ?, ?)",
             (chat_id, activity_name, now, interval_hours))
    activity_id = c.lastrowid
    conn.commit()
    conn.close()
    return activity_id

def save_users(users, interval_hours, activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()

    # حذف نوبت‌های قبلی این فعالیت
    c.execute("DELETE FROM turns WHERE activity_id = ?", (activity_id,))

    now = get_tehran_time()
    for i, user in enumerate(users):
        turn_date = now + timedelta(hours=i * interval_hours)
        c.execute("INSERT INTO turns (activity_id, name, username, turn_date, score) VALUES (?, ?, ?, ?, 0)",
                 (activity_id, user['name'], user['username'], turn_date.strftime("%Y-%m-%d %H:%M")))

    conn.commit()
    conn.close()

def update_turn_intervals(activity_id, interval_hours):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()

    # گرفتن لیست کاربران این فعالیت
    c.execute("SELECT name, username FROM turns WHERE activity_id = ? GROUP BY name", (activity_id,))
    users = c.fetchall()

    # حذف نوبت‌های قبلی این فعالیت
    c.execute("DELETE FROM turns WHERE activity_id = ?", (activity_id,))

    # ایجاد نوبت‌های جدید با فاصله جدید
    now = get_tehran_time()
    for i, user in enumerate(users):
        turn_date = now + timedelta(hours=i * interval_hours)
        c.execute("INSERT INTO turns (activity_id, name, username, turn_date, score) VALUES (?, ?, ?, ?, ?)",
                 (activity_id, user[0], user[1], turn_date.strftime("%Y-%m-%d %H:%M"), 0))

    conn.commit()
    conn.close()

def get_activity_name(activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()
    c.execute("SELECT name FROM activities WHERE id = ?", (activity_id,))
    result = c.fetchone()
    conn.close()

    if result:
        return result[0]
    return "فعالیت"

def get_activity_interval(activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()
    c.execute("SELECT interval_hours FROM activities WHERE id = ?", (activity_id,))
    result = c.fetchone()
    conn.close()

    if result:
        return result[0]
    return 1  # پیش‌فرض 1 ساعت

def get_all_activities(chat_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM activities WHERE chat_id = ? ORDER BY created_date", (chat_id,))
    results = c.fetchall()
    conn.close()

    return [{'id': result[0], 'name': result[1]} for result in results]

def get_current_turn(activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()

    # استفاده از زمان تهران برای مقایسه
    now_tehran = get_tehran_time().strftime("%Y-%m-%d %H:%M")
    c.execute("SELECT name, username, turn_date FROM turns WHERE activity_id = ? AND turn_date <= ? ORDER BY turn_date LIMIT 1",
             (activity_id, now_tehran))
    result = c.fetchone()
    conn.close()

    if result:
        return {'name': result[0], 'username': result[1], 'turn_date': result[2]}
    return None

def get_next_turns(limit, activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()
    c.execute("SELECT name, username, turn_date FROM turns WHERE activity_id = ? ORDER BY turn_date LIMIT ?",
             (activity_id, limit))
    results = c.fetchall()
    conn.close()

    return [{'name': result[0], 'username': result[1], 'turn_date': result[2]} for result in results]

def move_to_next_turn(current_user_name, activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()

    # پیدا کردن فاصله نوبت‌ها از جدول activities
    interval_hours = get_activity_interval(activity_id)

    # پیدا کردن کاربر فعلی
    c.execute("SELECT turn_date FROM turns WHERE activity_id = ? AND name = ?", (activity_id, current_user_name))
    current_turn = c.fetchone()

    if current_turn:
        # پیدا کردن آخرین تاریخ در این فعالیت
        c.execute("SELECT MAX(turn_date) FROM turns WHERE activity_id = ?", (activity_id,))
        max_date = c.fetchone()[0]

        # محاسبه تاریخ جدید با استفاده از فاصله واقعی
        max_date_obj = datetime.strptime(max_date, "%Y-%m-%d %H:%M")
        max_date_obj = tehran_tz.localize(max_date_obj)
        new_date = max_date_obj + timedelta(hours=interval_hours)

        # آپدیت تاریخ کاربر (سیستم چرخشی)
        c.execute("UPDATE turns SET turn_date = ? WHERE activity_id = ? AND name = ?",
                 (new_date.strftime("%Y-%m-%d %H:%M"), activity_id, current_user_name))

    conn.commit()
    conn.close()

def get_scores(activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()
    c.execute("SELECT name, score FROM turns WHERE activity_id = ? ORDER BY score DESC", (activity_id,))
    results = c.fetchall()
    conn.close()

    return [{'name': r[0], 'score': r[1]} for r in results]

def update_score(name, score, activity_id):
    conn = sqlite3.connect('sweep_bot.db')
    c = conn.cursor()
    c.execute("UPDATE turns SET score = score + ? WHERE activity_id = ? AND name = ?", (score, activity_id, name))
    conn.commit()
    conn.close()
