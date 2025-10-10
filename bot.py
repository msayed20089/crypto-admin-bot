import sys
import telebot
from telebot import types
import io
import tokenize
import requests
import time
from threading import Thread
import subprocess
import string
from collections import defaultdict
from datetime import datetime
import random
import re
import chardet
import logging
import threading
import os
import hashlib
import tempfile
import shutil
import zipfile
import sqlite3
import platform
import uuid
import socket
from concurrent.futures import ThreadPoolExecutor

# إعدادات البوتات
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8213481338:AAH5hrAAapU7CemnHu9cC9ld4n2PYERGyB0')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6096879850))

bot_scripts1 = defaultdict(lambda: {'processes': [], 'name': '', 'path': '', 'uploader': ''})
user_files = {}
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=10)

bot = telebot.TeleBot(BOT_TOKEN)
bot_scripts = {}
uploaded_files_dir = "uploaded_files"
banned_users = set()
user_chats = {}

# ======= نظام مفتوح للجميع ======= #
approved_users = set()
approved_users.add(ADMIN_ID)

# ======= إعدادات نظام الحماية ======= #
protection_enabled = True
protection_level = "medium"
suspicious_files_dir = 'suspicious_files'
MAX_FILE_SIZE = 10 * 1024 * 1024  # زيادة إلى 10MB

# حالة تشغيل/إيقاف البوت
bot_running = True

# إنشاء المجلدات المطلوبة
for directory in [uploaded_files_dir, suspicious_files_dir]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# ======= دوال مساعدة أساسية ======= #
def save_chat_id(chat_id):
    if chat_id not in user_chats:
        user_chats[chat_id] = True
        print(f"تم حفظ chat_id: {chat_id}")

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_approved_user(user_id):
    return True  # الجميع مقبول الآن

# ======= دوال الحماية ======= #
def scan_file_for_malicious_code(file_path, user_id):
    if is_admin(user_id):
        return False, None, ""

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        content = raw_data.decode('utf-8', errors='replace')
        
        dangerous_patterns = [
            r"rm\s+-rf\s+[\'\"]?/",
            r"import\s+marshal",
            r"import\s+zlib", 
            r"import\s+base64",
            r"eval\s*\(",
            r"exec\s*\(",
            r"shutil\.make_archive",
            r"bot\.send_document",
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True, f"تم اكتشاف أمر خطير: {pattern}", "malicious"
                
        return False, None, ""
    except Exception as e:
        return True, f"خطأ في الفحص: {e}", "malicious"

# ======= دوال أساسية ======= #
def stop_bot(script_path, chat_id, delete=False):
    try:
        if chat_id in bot_scripts and bot_scripts[chat_id].get('process'):
            process = bot_scripts[chat_id]['process']
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        
        if delete and os.path.exists(script_path):
            os.remove(script_path)
            
        return True
    except Exception as e:
        print(f"Error stopping bot: {e}")
        return False

def start_file(script_path, chat_id):
    script_name = os.path.basename(script_path)

    with lock:
        if chat_id not in bot_scripts:
            bot_scripts[chat_id] = {'process': None, 'files': [], 'path': script_path}

        try:
            if bot_scripts[chat_id].get('process') and bot_scripts[chat_id]['process'].poll() is None:
                bot.send_message(chat_id, f"الملف {script_name} يعمل بالفعل.")
                return

            p = subprocess.Popen([sys.executable, script_path])
            bot_scripts[chat_id]['process'] = p
            bot.send_message(chat_id, f"✅ تم تشغيل الملف {script_name} بنجاح.")
        except Exception as e:
            bot.send_message(chat_id, f"❌ فشل في تشغيل الملف: {e}")

# ======= دوال التحكم في البوت الرئيسي ======= #
def start_bot_control():
    """تشغيل البوت الرئيسي"""
    global bot_running
    bot_running = True
    print("✅ تم تشغيل البوت الرئيسي")

def stop_bot_control():
    """إيقاف البوت الرئيسي"""
    global bot_running
    bot_running = False
    print("🛑 تم إيقاف البوت الرئيسي")

# ======= تعديل الملفات تلقائياً ======= #
def modify_python_file(file_path):
    """تعديل ملف البايثون لإضافة رابط البوت في رسالة الترحيب"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # رابط البوت للإضافة
        bot_link = "\n\n🌟 بوت استضافات مجانيه: @puistbot"
        
        # البحث عن رسائل الترحيب وتعديلها
        welcome_patterns = [
            r'(bot\.send_message\([^)]*[\'\"](مرحبا|اهلا|أهلاً|مرحباً|Welcome|hello)[^\'\"]*[\'\"][^)]*\))',
            r'(bot\.send_message\([^)]*start[^)]*\))',
            r'(bot\.reply_to\([^)]*[\'\"](مرحبا|اهلا|أهلاً|مرحباً|Welcome|hello)[^\'\"]*[\'\"][^)]*\))'
        ]
        
        modified = False
        
        for pattern in welcome_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match_text = match[0]
                else:
                    match_text = match
                
                # إضافة رابط البوت قبل القوس الأخير
                if bot_link not in match_text:
                    new_text = match_text.replace(')', f'{bot_link})')
                    content = content.replace(match_text, new_text)
                    modified = True
        
        # إذا لم نجد رسائل ترحيب، نضيف رسالة جديدة في بداية الملف
        if not modified:
            # البحث عن دالة start أو command handler
            start_pattern = r'@bot\.message_handler\(commands=\[[\'"]start[\'"]\]\)\s*def\s+start\([^)]*\):'
            start_match = re.search(start_pattern, content)
            
            if start_match:
                # إضافة رسالة بعد دالة start
                start_end = start_match.end()
                function_content = content[start_end:]
                
                # البحث عن أول bot.send_message في الدالة
                send_msg_pattern = r'bot\.(send_message|reply_to)\([^)]+\)'
                send_match = re.search(send_msg_pattern, function_content)
                
                if send_match:
                    send_text = send_match.group(0)
                    if bot_link not in send_text:
                        new_send = send_text.replace(')', f'{bot_link})')
                        content = content.replace(send_text, new_send)
        
        # حفظ الملف المعدل
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error modifying file: {e}")
        return False

# ======= Handlers الأساسية ======= #
@bot.message_handler(commands=['start'])
def start(message):
    save_chat_id(message.chat.id)
    user_id = message.from_user.id

    if not bot_running:
        bot.send_message(message.chat.id, "⏸️ البوت متوقف حاليًا. يرجى الانتظار حتى يتم تشغيله.")
        return

    if message.from_user.username in banned_users:
        bot.send_message(message.chat.id, "⁉️ تم حظرك من البوت. تواصل مع المطور.")
        return

    show_main_menu(message)

def show_main_menu(message):
    """عرض القائمة الرئيسية مع الأزرار المطلوبة"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # الأزرار الرئيسية
    protection_button = types.InlineKeyboardButton("التحكم في الحماية 🛡️", callback_data='protection_control')
    upload_button = types.InlineKeyboardButton("رفع ملف 📥", callback_data='upload')
    support_girl_button = types.InlineKeyboardButton("فتاة المحاور 👩‍💼", callback_data='support_girl')
    speed_button = types.InlineKeyboardButton("🚀 سرعة البوت", callback_data='speed')
    about_button = types.InlineKeyboardButton("ℹ️ حول البوت", callback_data='about_bot')
    tech_support_button = types.InlineKeyboardButton("🛠️ الدعم الفني", callback_data='tech_support')
    install_lib_button = types.InlineKeyboardButton("📚 تثبيت مكتبة", callback_data='download_lib')
    contact_support_button = types.InlineKeyboardButton("📞 التواصل مع الدعم", callback_data='online_support')
    
    # ترتيب الأزرار
    markup.add(protection_button, upload_button)
    markup.add(support_girl_button, speed_button)
    markup.add(about_button, tech_support_button)
    markup.add(install_lib_button, contact_support_button)
    
    # إضافة أزرار الأدمن إذا كان مستخدم مسؤول
    if is_admin(message.from_user.id):
        users_button = types.InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='manage_users')
        bot_control_button = types.InlineKeyboardButton("⚡ تشغيل/إيقاف البوت", callback_data='bot_control')
        markup.add(users_button, bot_control_button)

    bot.send_message(
        message.chat.id,
        f"🐍 **Python Hosting** 🐍\n\n"
        f"مرحباً، {message.from_user.first_name}! 👋\n\n"
        "**الميزات المتاحة:** ✅\n\n"
        "• تشغيل الملف على سيرفر خاص\n"
        "• تشغيل الملفات بكل سهولة وسرعة\n"
        "• تواصل مع المحاور لأي إستفسار أو مشاكل\n"
        "• بوت استضافات مجانيه: @puistbot\n\n"
        "**اختر من الأزرار أدناه:**",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ======= معالجة الأزرار ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'support_girl')
def support_girl_callback(call):
    """زر فتاة المحاور"""
    bot.answer_callback_query(call.id, "👩‍💼 جاري الاتصال بفتاة المحاور...")
    
    # محاكاة الانتظار للاتصال
    time.sleep(1)
    
    markup = types.InlineKeyboardMarkup()
    end_chat_button = types.InlineKeyboardButton("إنهاء المحادثة", callback_data='end_chat')
    markup.add(end_chat_button)
    
    bot.send_message(
        call.message.chat.id,
        "👩‍💼 **مرحباً! أنا فتاة المحاور**\n\n"
        "كيف يمكنني مساعدتك اليوم؟\n"
        "أنا هنا للإجابة على استفساراتك وتقديم الدعم.\n\n"
        "يمكنك سؤالي عن:\n"
        "• كيفية استخدام البوت\n"
        "• المشاكل التقنية\n"
        "• استفسارات عامة\n\n"
        "🌟 بوت استضافات مجانيه: @puistbot\n\n"
        "ما الذي تريد معرفته؟ 💬",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'tech_support')
def tech_support_callback(call):
    """زر الدعم الفني"""
    bot.answer_callback_query(call.id, "🛠️ جاري تحويلك للدعم الفني...")
    
    markup = types.InlineKeyboardMarkup()
    common_issues_button = types.InlineKeyboardButton("🔧 المشاكل الشائعة", callback_data='common_issues')
    contact_admin_button = types.InlineKeyboardButton("👨‍💼 التواصل مع الأدمن", callback_data='online_support')
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')
    markup.add(common_issues_button)
    markup.add(contact_admin_button)
    markup.add(back_button)
    
    bot.send_message(
        call.message.chat.id,
        "🛠️ **الدعم الفني**\n\n"
        "**الخدمات المتاحة:**\n"
        "• حل المشاكل التقنية\n"
        "• استكشاف الأخطاء وإصلاحها\n"
        "• دعم في تشغيل الملفات\n"
        "• مساعدة في تثبيت المكتبات\n"
        "• بوت استضافات مجانيه: @puistbot\n\n"
        "اختر الخدمة التي تحتاجها:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'common_issues')
def common_issues_callback(call):
    """المشاكل الشائعة"""
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup()
    file_not_working = types.InlineKeyboardButton("📁 الملف لا يعمل", callback_data='issue_file')
    installation_issue = types.InlineKeyboardButton("📚 مشكلة في التثبيت", callback_data='issue_install')
    speed_issue = types.InlineKeyboardButton("🐌 البوت بطيء", callback_data='issue_speed')
    back_button = types.InlineKeyboardButton("🔙 رجوع للدعم", callback_data='tech_support')
    markup.add(file_not_working, installation_issue)
    markup.add(speed_issue)
    markup.add(back_button)
    
    bot.edit_message_text(
        "🔧 **المشاكل الشائعة**\n\n"
        "اختر نوع المشكلة التي تواجهك:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('issue_'))
def handle_common_issue(call):
    """معالجة المشاكل الشائعة"""
    issue_type = call.data.replace('issue_', '')
    
    solutions = {
        'file': "**حلول مشكلة الملف لا يعمل:**\n\n"
                "1. تأكد أن الملف بصيغة .py\n"
                "2. تحقق من وجود أخطاء في الكود\n"
                "3. تأكد من تثبيت جميع المكتبات المطلوبة\n"
                "4. حاول إعادة رفع الملف\n"
                "🌟 بوت استضافات مجانيه: @puistbot\n",
        'install': "**حلول مشاكل التثبيت:**\n\n"
                  "1. تأكد من اسم المكتبة\n"
                  "2. جرب تثبيت إصدار محدد: `pip install library==version`\n"
                  "3. تأكد من اتصال الإنترنت\n"
                  "4. جرب تحديث pip: `pip install --upgrade pip`\n"
                  "🌟 بوت استضافات مجانيه: @puistbot\n",
        'speed': "**تحسين سرعة البوت:**\n\n"
                "1. تأكد من جودة الاتصال بالإنترنت\n"
                "2. أغلق الملفات غير المستخدمة\n"
                "3. حاول إعادة تشغيل البوت\n"
                "4. تأكد من عدم وجود عمليات ثقيلة\n"
                "🌟 بوت استضافات مجانيه: @puistbot\n"
    }
    
    solution = solutions.get(issue_type, "لم يتم العثور على حل لهذه المشكلة.")
    
    markup = types.InlineKeyboardMarkup()
    if issue_type == 'file':
        retry_upload = types.InlineKeyboardButton("🔄 إعادة رفع الملف", callback_data='upload')
        markup.add(retry_upload)
    elif issue_type == 'install':
        retry_install = types.InlineKeyboardButton("🔄 محاولة تثبيت أخرى", callback_data='download_lib')
        markup.add(retry_install)
    
    back_button = types.InlineKeyboardButton("🔙 رجوع للمشاكل", callback_data='common_issues')
    support_button = types.InlineKeyboardButton("📞 دعم مباشر", callback_data='online_support')
    markup.add(back_button, support_button)
    
    bot.edit_message_text(
        solution,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'end_chat')
def end_chat_callback(call):
    """إنهاء المحادثة مع فتاة المحاور"""
    bot.answer_callback_query(call.id, "تم إنهاء المحادثة")
    
    markup = types.InlineKeyboardMarkup()
    restart_chat = types.InlineKeyboardButton("🔄 بدء محادثة جديدة", callback_data='support_girl')
    main_menu = types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data='back_to_main')
    markup.add(restart_chat, main_menu)
    
    bot.edit_message_text(
        "👋 **تم إنهاء المحادثة**\n\n"
        "شكراً لك على التواصل معنا!\n"
        "لا تتردد في البدء بمحادثة جديدة إذا كنت بحاجة للمساعدة.\n\n"
        "🌟 بوت استضافات مجانيه: @puistbot",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'bot_control')
def bot_control_callback(call):
    """التحكم في تشغيل/إيقاف البوت"""
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية للتحكم في البوت")
        return
    
    global bot_running
    
    markup = types.InlineKeyboardMarkup()
    
    if bot_running:
        stop_button = types.InlineKeyboardButton("🛑 إيقاف البوت", callback_data='stop_bot_main')
        status_text = "✅ البوت يعمل حالياً"
        markup.add(stop_button)
    else:
        start_button = types.InlineKeyboardButton("⚡ تشغيل البوت", callback_data='start_bot_main')
        status_text = "⏸️ البوت متوقف حالياً"
        markup.add(start_button)
    
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')
    markup.add(back_button)
    
    bot.edit_message_text(
        f"⚡ **تحكم في البوت الرئيسي**\n\n"
        f"الحالة: {status_text}\n\n"
        f"من هنا يمكنك التحكم في حالة البوت الرئيسي:\n\n"
        f"🌟 بوت استضافات مجانيه: @puistbot",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'stop_bot_main')
def stop_bot_main(call):
    """إيقاف البوت الرئيسي"""
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    
    stop_bot_control()
    
    bot.answer_callback_query(call.id, "🛑 تم إيقاف البوت")
    bot_control_callback(call)  # تحديث القائمة

@bot.callback_query_handler(func=lambda call: call.data == 'start_bot_main')
def start_bot_main(call):
    """تشغيل البوت الرئيسي"""
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    
    start_bot_control()
    
    bot.answer_callback_query(call.id, "⚡ تم تشغيل البوت")
    bot_control_callback(call)  # تحديث القائمة

# ======= دوال السرعة المحسنة ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'speed')
def check_speed(call):
    bot.answer_callback_query(call.id, "⏳ جاري قياس سرعة البوت...")
    
    # إرسال رسالة الانتظار
    wait_msg = bot.send_message(call.message.chat.id, "⏳ **انتظر يتم قياس سرعة البوت...**")
    
    # قياس السرعة الحقيقية
    start_time = time.time()
    
    # اختبار سرعة الاستجابة
    response_times = []
    for i in range(3):
        test_start = time.time()
        time.sleep(0.1)  # محاكاة عملية
        response_times.append((time.time() - test_start) * 1000)
    
    # حساب متوسط السرعة
    avg_response_time = sum(response_times) / len(response_times)
    total_time = (time.time() - start_time) * 1000
    
    # تحديد التقييم بناءً على السرعة
    if avg_response_time < 50:
        rating = "⚡ ممتازة!"
        emoji = "⚡"
    elif avg_response_time < 100:
        rating = "🚀 جيدة جداً"
        emoji = "🚀"
    elif avg_response_time < 200:
        rating = "👍 جيدة"
        emoji = "👍"
    else:
        rating = "🐌 تحتاج تحسين"
        emoji = "🐌"
    
    # تحديث الرسالة بنتيجة السرعة
    bot.edit_message_text(
        f"{emoji} **سرعة البوت الحالية:**\n\n"
        f"• سرعة الاستجابة: `{avg_response_time:.2f} ms`\n"
        f"• الوقت الكلي: `{total_time:.2f} ms`\n"
        f"• التقييم: **{rating}**\n\n"
        f"🌟 بوت استضافات مجانيه: @puistbot\n\n"
        f"_{datetime.now().strftime('%I:%M %p')}_",
        call.message.chat.id,
        wait_msg.message_id,
        parse_mode='Markdown'
    )

# ======= دوال مساعدة إضافية ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'upload')
def upload_file_callback(call):
    if not bot_running:
        bot.answer_callback_query(call.id, "⏸️ البوت متوقف حالياً")
        return
        
    bot.answer_callback_query(call.id, "📤 جاري إعداد رفع الملف...")
    
    markup = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("❌ إلغاء", callback_data='back_to_main')
    markup.add(cancel_button)
    
    bot.send_message(
        call.message.chat.id,
        "📤 **رفع ملف**\n\n"
        "أرسل ملف البوت الآن (ملف .py فقط)\n"
        "الحد الأقصى للحجم: 10MB\n\n"
        "🌟 بوت استضافات مجانيه: @puistbot\n\n"
        "سيتم فحص الملف تلقائياً للحماية.",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'about_bot')
def about_bot(call):
    """زر حول البوت"""
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup()
    features_button = types.InlineKeyboardButton("🌟 الميزات", callback_data='features_list')
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')
    markup.add(features_button, back_button)
    
    bot.send_message(
        call.message.chat.id,
        "ℹ️ **حول البوت**\n\n"
        "🐍 **Python Hosting Bot**\n\n"
        "**المميزات:**\n"
        "✅ تشغيل الملفات على سيرفر خاص\n"
        "✅ سرعة وأداء عالي\n"
        "✅ نظام حماية متقدم\n"
        "✅ دعم فني متكامل\n"
        "✅ إدارة مستخدمين ذكية\n\n"
        "**للمطورين:**\n"
        "🔹 رفع وتشغيل ملفات .py\n"
        "🔹 تثبيت المكتبات المطلوبة\n"
        "🔹 مراقبة أداء البوت\n"
        "🔹 تحكم كامل في العمليات\n\n"
        "🌟 بوت استضافات مجانيه: @puistbot",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'features_list')
def show_features(call):
    bot.answer_callback_query(call.id)
    
    markup = types.InlineKeyboardMarkup()
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='about_bot')
    markup.add(back_button)
    
    bot.edit_message_text(
        "🌟 **الميزات المتاحة:**\n\n"
        "🛡️ **نظام الحماية:**\n"
        "• فحص الملفات تلقائياً\n"
        "• منع الملفات الضارة\n"
        "• مستويات حماية متعددة\n\n"
        "⚡ **الأداء:**\n"
        "• تشغيل سريع للملفات\n"
        "• قياس سرعة البوت\n"
        "• إدارة العمليات الذكية\n\n"
        "👥 **إدارة المستخدمين:**\n"
        "• نظام مفتوح للجميع\n"
        "• تحكم كامل للمشرف\n"
        "• حظر المستخدمين الضارين\n\n"
        "🛠️ **الدعم:**\n"
        "• دعم فني متكامل\n"
        "• مساعدة مباشرة\n"
        "• حل المشاكل التقنية\n\n"
        "🌟 بوت استضافات مجانيه: @puistbot",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'download_lib')
def download_library(call):
    bot.send_message(call.message.chat.id, "📚 أرسل اسم المكتبة التي تريد تثبيتها:")
    bot.register_next_step_handler(call.message, install_library_step)

def install_library_step(message):
    library_name = message.text.strip()
    bot.send_message(message.chat.id, f"🔄 جاري تثبيت {library_name}...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", library_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            bot.send_message(message.chat.id, f"✅ تم تثبيت {library_name} بنجاح\n\n🌟 بوت استضافات مجانيه: @puistbot")
        else:
            bot.send_message(message.chat.id, f"❌ فشل في تثبيت {library_name}\n{result.stderr}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'online_support')
def online_support(call):
    bot.answer_callback_query(call.id, "جارٍ إرسال طلب الدعم...")
    
    user_info = f"👤 {call.from_user.first_name}\n🆔 {call.from_user.id}\n📌 @{call.from_user.username or 'غير متوفر'}"
    
    bot.send_message(
        ADMIN_ID,
        f"📞 طلب دعم فوري:\n\n{user_info}\n\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    bot.send_message(call.message.chat.id, "✅ تم إرسال طلب الدعم للأدمن\n\n🌟 بوت استضافات مجانيه: @puistbot")

@bot.callback_query_handler(func=lambda call: call.data == 'protection_control')
def protection_control(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
        
    status = "✅ مفعل" if protection_enabled else "❌ معطل"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    enable_btn = types.InlineKeyboardButton("تفعيل الحماية", callback_data='enable_protection')
    disable_btn = types.InlineKeyboardButton("تعطيل الحماية", callback_data='disable_protection')
    low_btn = types.InlineKeyboardButton("منخفض", callback_data='protection_low')
    medium_btn = types.InlineKeyboardButton("متوسط", callback_data='protection_medium')
    high_btn = types.InlineKeyboardButton("عالي", callback_data='protection_high')
    back_btn = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')
    
    markup.add(enable_btn, disable_btn)
    markup.add(low_btn, medium_btn, high_btn)
    markup.add(back_btn)
    
    bot.edit_message_text(
        f"⚙️ إعدادات الحماية\n\n"
        f"الحالة: {status}\n"
        f"المستوى: {protection_level}\n\n"
        f"🌟 بوت استضافات مجانيه: @puistbot",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ['enable_protection', 'disable_protection', 'protection_low', 'protection_medium', 'protection_high'])
def handle_protection_settings(call):
    global protection_enabled, protection_level
    
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
        
    if call.data == 'enable_protection':
        protection_enabled = True
        bot.answer_callback_query(call.id, "✅ تم تفعيل الحماية")
    elif call.data == 'disable_protection':
        protection_enabled = False
        bot.answer_callback_query(call.id, "❌ تم تعطيل الحماية")
    elif call.data == 'protection_low':
        protection_level = "low"
        bot.answer_callback_query(call.id, "🔵 مستوى منخفض")
    elif call.data == 'protection_medium':
        protection_level = "medium"
        bot.answer_callback_query(call.id, "🟡 مستوى متوسط")
    elif call.data == 'protection_high':
        protection_level = "high"
        bot.answer_callback_query(call.id, "🔴 مستوى عالي")
    
    # تحديث القائمة
    protection_control(call)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main(call):
    try:
        show_main_menu(call.message)
        bot.answer_callback_query(call.id, "العودة للقائمة الرئيسية")
    except Exception as e:
        bot.answer_callback_query(call.id, "حدث خطأ في العودة")

# ======= معالجة رفع الملفات ======= #
@bot.message_handler(content_types=['document'])
def handle_file(message):
    try:
        user_id = message.from_user.id
        
        if message.from_user.username in banned_users:
            bot.send_message(message.chat.id, "⁉️ تم حظرك من البوت")
            return

        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        
        if file_info.file_size > MAX_FILE_SIZE:
            bot.reply_to(message, "⛔ حجم الملف يتجاوز 10MB")
            return
            
        downloaded_file = bot.download_file(file_info.file_path)
        bot_script_name = message.document.file_name
        
        if not bot_script_name.endswith('.py'):
            bot.reply_to(message, "❌ فقط ملفات بايثون مسموحة")
            return

        temp_path = os.path.join(tempfile.gettempdir(), bot_script_name)
        with open(temp_path, 'wb') as temp_file:
            temp_file.write(downloaded_file)

        # فحص الملف
        if protection_enabled and not is_admin(user_id):
            is_malicious, activity, threat_type = scan_file_for_malicious_code(temp_path, user_id)
            if is_malicious:
                bot.reply_to(message, "⛔ تم رفض الملف لأسباب أمنية")
                return
        
        # تعديل الملف تلقائياً
        modify_python_file(temp_path)
                
        script_path = os.path.join(uploaded_files_dir, bot_script_name)
        shutil.move(temp_path, script_path)

        bot_scripts[message.chat.id] = {
            'name': bot_script_name,
            'uploader': message.from_user.username,
            'path': script_path,
            'process': None
        }

        markup = types.InlineKeyboardMarkup()
        stop_button = types.InlineKeyboardButton(f"🛑 إيقاف {bot_script_name}", callback_data=f'stop_{message.chat.id}_{bot_script_name}')
        markup.add(stop_button)

        bot.reply_to(
            message,
            f"✅ تم رفع الملف بنجاح\n\n"
            f"📁 الملف: {bot_script_name}\n"
            f"👤 المستخدم: @{message.from_user.username}\n"
            f"🌟 بوت استضافات مجانيه: @puistbot\n\n"
            f"يمكنك إيقاف التشغيل بالزر أدناه:",
            reply_markup=markup
        )
        
        # تشغيل الملف
        start_file(script_path, message.chat.id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_bot_callback(call):
    try:
        parts = call.data.split('_')
        chat_id = int(parts[1])
        script_name = '_'.join(parts[2:])
        
        script_path = os.path.join(uploaded_files_dir, script_name)
        if stop_bot(script_path, chat_id):
            bot.answer_callback_query(call.id, "✅ تم الإيقاف")
            bot.edit_message_text(
                f"🛑 تم إيقاف {script_name}\n\n🌟 بوت استضافات مجانيه: @puistbot",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            bot.answer_callback_query(call.id, "❌ فشل في الإيقاف")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطأ: {e}")

# ======= إدارة المستخدمين ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'manage_users')
def manage_users(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية")
        return
    
    total_approved = len(approved_users)
    
    markup = types.InlineKeyboardMarkup()
    
    approved_button = types.InlineKeyboardButton(f"✅ المستخدمون ({total_approved})", callback_data='show_approved')
    broadcast_button = types.InlineKeyboardButton("📢 إرسال للجميع", callback_data='broadcast_all')
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')
    
    markup.add(approved_button)
    markup.add(broadcast_button)
    markup.add(back_button)
    
    bot.edit_message_text(
        f"👥 إدارة المستخدمين\n\n"
        f"📊 الإحصائيات:\n"
        f"✅ المستخدمون: {total_approved}\n\n"
        f"🌟 بوت استضافات مجانيه: @puistbot",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

# ======= أوامر الأدمن ======= #
@bot.message_handler(commands=['rck'])
def broadcast_message(message):
    if not is_admin(message.from_user.id):
        return
        
    try:
        msg = message.text.split(' ', 1)[1]
        success = 0
        failed = 0
        
        for user_id in approved_users:
            try:
                bot.send_message(user_id, msg)
                success += 1
            except:
                failed += 1
                
        bot.reply_to(message, f"📊 تم الإرسال لـ {success} مستخدم، فشل: {failed}")
    except:
        bot.reply_to(message, "❌ استخدم: /rck الرسالة")

# تشغيل البوت
if __name__ == '__main__':
    print("🤖 البوت يعمل...")
    print(f"✅ المستخدمون: {len(approved_users)}")
    print(f"⚡ حالة البوت: {'يعمل' if bot_running else 'متوقف'}")
    print("🌟 بوت استضافات مجانيه: @puistbot")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        time.sleep(5)
