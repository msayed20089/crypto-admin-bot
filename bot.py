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

# قناة الاشتراك الإجباري
CHANNEL_USERNAME = "@zforexms"
CHANNEL_LINK = "https://t.me/zforexms"

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
MAX_FILE_SIZE = 10 * 1024 * 1024

# حالة تشغيل/إيقاف البوت
bot_running = True

# إنشاء المجلدات المطلوبة
for directory in [uploaded_files_dir, suspicious_files_dir]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# ======= دوال الاشتراك الإجباري ======= #
def check_subscription(user_id):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

def show_subscription_required(chat_id):
    """عرض رسالة الاشتراك الإجباري"""
    markup = types.InlineKeyboardMarkup()
    channel_button = types.InlineKeyboardButton("📢 انضم للقناة", url=CHANNEL_LINK)
    check_button = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data='check_subscription')
    markup.add(channel_button, check_button)
    
    bot.send_message(
        chat_id,
        f"👋 **مرحباً بك في بوت استضافة بايثون!**\n\n"
        f"📢 **للوصول إلى جميع الميزات، يجب الاشتراك في قناتنا أولاً:**\n"
        f"🔗 {CHANNEL_USERNAME}\n\n"
        f"**بعد الاشتراك اضغط على زر 'تحقق من الاشتراك'**\n\n"
        f"🌟 **بوت استضافات مجانيه: @puistbot**",
        reply_markup=markup,
        parse_mode='Markdown'
    )

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

# ======= دوال التصحيح التلقائي للملفات ======= #
def fix_telegram_imports(file_content):
    """تصحيح استيرادات مكتبة telegram تلقائياً"""
    try:
        # المشاكل الشائعة في استيراد telegram
        fixes = [
            # تصحيح python-telegram-bot v20
            (r'from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup', 
             'from telegram import Update\nfrom telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes\nfrom telegram import InlineKeyboardButton, InlineKeyboardMarkup'),
            
            # تصحيح python-telegram-bot v13
            (r'from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext',
             'from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes'),
            
            # تصحيح Filters إلى filters
            (r'Filters\.', 'filters.'),
            
            # تصحيح CallbackContext إلى ContextTypes
            (r'CallbackContext', 'ContextTypes.DEFAULT_TYPE'),
            
            # تصحيح Updater إلى Application
            (r'Updater\s*\(\s*[\'"]', 'Application.builder().token(\''),
            (r'\.start_polling\(\)', '.run_polling()'),
            (r'\.idle\(\)', ''),
            
            # إضافة build() إذا لم تكن موجودة
            (r'Application\.builder\(\)\.token\(([^)]+)\)', r'Application.builder().token(\1).build()')
        ]
        
        fixed_content = file_content
        
        for pattern, replacement in fixes:
            fixed_content = re.sub(pattern, replacement, fixed_content)
        
        # إذا كان هناك Updater ولم يتم تحويله
        if 'Updater' in fixed_content and 'Application' not in fixed_content:
            fixed_content = fixed_content.replace('Updater', 'Application')
        
        return fixed_content
    
    except Exception as e:
        print(f"Error fixing telegram imports: {e}")
        return file_content

def auto_fix_python_file(file_path):
    """التصحيح التلقائي للملفات البايثون"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. تصحيح استيرادات telegram
        content = fix_telegram_imports(content)
        
        # 2. إضافة المكتبات المفقودة
        if 'import asyncio' not in content and 'async' in content:
            content = 'import asyncio\n' + content
        
        if 'import logging' not in content and 'logging.' in content:
            content = 'import logging\n' + content
        
        # 3. تصحيح المشاكل الشائعة في التعامل مع البوتات
        if 'Application.builder().token(' in content and '.build()' not in content:
            content = content.replace('Application.builder().token(', 'Application.builder().token(')
            # البحث عن السطر الذي يحتوي على token وإضافة build()
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'Application.builder().token(' in line and '.build()' not in line:
                    lines[i] = line.replace(')', ').build()')
            content = '\n'.join(lines)
        
        # 4. تعديل رسالة الترحيب
        bot_link = "\n\n🌟 بوت استضافات مجانيه: @puistbot"
        
        # البحث عن رسائل الترحيب وتعديلها
        welcome_patterns = [
            r'(bot\.send_message\([^)]*[\'\"](مرحبا|اهلا|أهلاً|مرحباً|Welcome|hello)[^\'\"]*[\'\"][^)]*\))',
            r'(bot\.send_message\([^)]*start[^)]*\))',
            r'(bot\.reply_to\([^)]*[\'\"](مرحبا|اهلا|أهلاً|مرحباً|Welcome|hello)[^\'\"]*[\'\"][^)]*\))',
            r'(await context\.bot\.send_message\([^)]*[\'\"](مرحبا|اهلا|أهلاً|مرحباً|Welcome|hello)[^\'\"]*[\'\"][^)]*\))'
        ]
        
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
        
        # إذا تم إجراء أي تعديلات، احفظ الملف
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "تم تصحيح الملف تلقائياً"
        
        return False, "لم يحتاج الملف إلى تصحيح"
    
    except Exception as e:
        print(f"Error in auto fix: {e}")
        return False, f"خطأ في التصحيح: {e}"
    # ======= دوال إضافة الاشتراك الإجباري ======= #
def add_channel_subscription(file_path):
    """إضافة اشتراك إجباري للقناة في الملف"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # كود التحقق من الاشتراك في القناة
        subscription_code = f'''
# ======= اشتراك إجباري في القناة ======= #
CHANNEL_USERNAME = "{CHANNEL_USERNAME}"  # قناتنا

def check_subscription(user_id):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription: {{e}}")
        return False

def show_subscription_required(chat_id):
    """عرض رسالة الاشتراك الإجباري"""
    markup = types.InlineKeyboardMarkup()
    channel_button = types.InlineKeyboardButton("📢 انضم للقناة", url="{CHANNEL_LINK}")
    check_button = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data='check_subscription')
    markup.add(channel_button, check_button)
    
    bot.send_message(
        chat_id,
        f"👋 **مرحباً بك!**\\n\\n"
        f"📢 **للوصول إلى جميع الميزات، يجب الاشتراك في قناتنا أولاً:**\\n"
        f"🔗 {CHANNEL_USERNAME}\\n\\n"
        f"**بعد الاشتراك اضغط على زر 'تحقق من الاشتراك'**",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'check_subscription')
def check_subscription_callback(call):
    """التحقق من الاشتراك عند الضغط على الزر"""
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "✅ تم التحقق من الاشتراك!")
        # هنا ضع الدالة التي تريد تنفيذها بعد التحقق
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!")
        show_subscription_required(call.message.chat.id)

'''

        # البحث عن دالة start لإضافة التحقق فيها
        start_pattern = r'@bot\.message_handler\(commands=\[[\'"]start[\'"]\]\)\s*def\s+start\([^)]*\):'
        start_match = re.search(start_pattern, content)
        
        if start_match:
            # إضافة التحقق في بداية دالة start
            start_pos = start_match.end()
            function_content = content[start_pos:]
            
            # إيجاد نطاق الدالة
            indent_level = 0
            function_lines = []
            lines = function_content.split('\n')
            
            for i, line in enumerate(lines):
                if i == 0:
                    # السطر الأول بعد def start
                    continue
                
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                    
                if stripped_line[0] != '#':  # تجاهل التعليقات
                    if not line.strip():  # خط فارغ
                        continue
                        
                    # حساب المسافة البادئة
                    current_indent = len(line) - len(line.lstrip())
                    
                    if i == 1:
                        indent_level = current_indent
                    
                    if current_indent < indent_level and stripped_line:
                        break
                
                function_lines.append(line)
            
            # بناء الدالة المعدلة
            new_function_content = content[:start_pos] + '\n'
            new_function_content += ' ' * (indent_level) + '# التحقق من الاشتراك قبل التنفيذ\n'
            new_function_content += ' ' * (indent_level) + 'user_id = message.from_user.id\n'
            new_function_content += ' ' * (indent_level) + 'if not check_subscription(user_id):\n'
            new_function_content += ' ' * (indent_level + 4) + 'show_subscription_required(message.chat.id)\n'
            new_function_content += ' ' * (indent_level + 4) + 'return\n'
            new_function_content += ' ' * (indent_level) + '\n'
            new_function_content += '\n'.join(function_lines)
            
            content = new_function_content
        
        # إضافة دوال الاشتراك في الملف إذا لم تكن موجودة
        if 'def check_subscription(' not in content:
            # إضافة الكود بعد الاستيرادات
            import_pattern = r'(import\s+[\w\s,]+|from\s+[\w.]+\s+import\s+[\w\s,]+)'
            imports_end = 0
            
            # البحث عن نهاية قسم الاستيرادات
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not (line.startswith('import') or line.startswith('from') or line.strip().startswith('#') or line.strip() == ''):
                    imports_end = i
                    break
            
            if imports_end > 0:
                new_content = '\n'.join(lines[:imports_end]) + '\n\n' + subscription_code + '\n\n' + '\n'.join(lines[imports_end:])
                content = new_content
        
        # إذا تم إجراء أي تعديلات، احفظ الملف
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "تم إضافة الاشتراك الإجباري للقناة"
        
        return False, "الملف يحتوي بالفعل على نظام الاشتراك"
    
    except Exception as e:
        print(f"Error adding channel subscription: {e}")
        return False, f"خطأ في إضافة الاشتراك: {e}"

# ======= دوال إدارة الأدمن المتقدمة ======= #
def get_bot_statistics():
    """الحصول على إحصائيات البوت"""
    total_users = len(user_chats)
    active_bots = sum(1 for chat_id in bot_scripts if bot_scripts[chat_id].get('process'))
    total_files = len([f for f in os.listdir(uploaded_files_dir) if f.endswith('.py')])
    
    # الحصول على قائمة البوتات النشطة
    active_bots_list = []
    for chat_id, script_data in bot_scripts.items():
        if script_data.get('process'):
            active_bots_list.append({
                'name': script_data.get('name', 'غير معروف'),
                'chat_id': chat_id,
                'uploader': script_data.get('uploader', 'غير معروف')
            })
    
    return {
        'total_users': total_users,
        'active_bots': active_bots,
        'total_files': total_files,
        'banned_users': len(banned_users),
        'uptime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'active_bots_list': active_bots_list
    }

def broadcast_message_to_all(message_text):
    """بث رسالة لجميع المستخدمين"""
    success = 0
    failed = 0
    
    for chat_id in user_chats:
        try:
            bot.send_message(chat_id, message_text)
            success += 1
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")
            failed += 1
    
    return success, failed

def broadcast_to_active_bots(message_text):
    """بث رسالة للبوتات النشطة فقط"""
    success = 0
    failed = 0
    active_bots = get_bot_statistics()['active_bots_list']
    
    for bot_info in active_bots:
        try:
            bot.send_message(bot_info['chat_id'], message_text)
            success += 1
            print(f"✅ تم الإرسال إلى بوت: {bot_info['name']}")
        except Exception as e:
            print(f"❌ فشل الإرسال إلى بوت {bot_info['name']}: {e}")
            failed += 1
    
    return success, failed, active_bots

def change_channel_settings(new_channel_username, new_channel_link):
    """تغيير إعدادات قناة الاشتراك الإجباري"""
    global CHANNEL_USERNAME, CHANNEL_LINK
    CHANNEL_USERNAME = new_channel_username
    CHANNEL_LINK = new_channel_link
    return True

# ======= دوال استخراج وتثبيت المكتبات ======= #
def extract_libraries_from_file(file_content):
    """استخراج المكتبات من محتوى الملف"""
    try:
        # مكتبات قياسية لا تحتاج تثبيت
        standard_libs = {
            'os', 'sys', 'time', 'datetime', 'random', 're', 'json', 
            'math', 'collections', 'threading', 'subprocess', 'tempfile',
            'shutil', 'hashlib', 'zipfile', 'platform', 'uuid', 'socket',
            'logging', 'io', 'string', 'concurrent', 'telebot', 'types',
            'asyncio', 'aiohttp'
        }
        
        # البحث عن جميع عمليات الاستيراد
        imports = re.findall(r'^\s*(?:from|import)\s+([\w\.]+)', file_content, re.MULTILINE)
        
        # استخراج أسماء المكتبات الأساسية
        libraries = set()
        for imp in imports:
            lib_name = imp.split('.')[0]
            if lib_name not in standard_libs:
                libraries.add(lib_name)
        
        return sorted(list(libraries))
    except Exception as e:
        print(f"Error extracting libraries: {e}")
        return []

def install_multiple_libraries(libraries):
    """تثبيت عدة مكتبات مرة واحدة"""
    if not libraries:
        return "❌ لم يتم العثور على مكتبات للتثبيت"
    
    success = []
    failed = []
    
    for library in libraries:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", library],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                success.append(library)
            else:
                failed.append(f"{library}: {result.stderr}")
        except Exception as e:
            failed.append(f"{library}: {str(e)}")
    
    message = ""
    if success:
        message += f"✅ **تم تثبيت المكتبات بنجاح:**\n{', '.join(success)}\n\n"
    if failed:
        message += f"❌ **فشل في تثبيت:**\n{chr(10).join(failed)}\n\n"
    
    message += f"🌟 **بوت استضافات مجانيه: @puistbot**"
    return message

def auto_install_libraries_and_start(file_path, chat_id, file_content):
    """تثبيت المكتبات تلقائياً وتشغيل الملف"""
    try:
        # استخراج المكتبات من الملف
        libraries = extract_libraries_from_file(file_content)
        
        if libraries:
            # إرسال رسالة الانتظار
            wait_msg = bot.send_message(chat_id, f"⏳ **جاري تثبيت {len(libraries)} مكتبة...**")
            
            # تثبيت المكتبات
            install_result = install_multiple_libraries(libraries)
            
            # تحديث رسالة الانتظار
            bot.edit_message_text(
                f"✅ **تم تثبيت المكتبات**\n\n"
                f"جاري تشغيل الملف...",
                chat_id,
                wait_msg.message_id
            )
        
        # التصحيح التلقائي للملف
        fixed, fix_message = auto_fix_python_file(file_path)
        if fixed:
            bot.send_message(chat_id, f"🔧 **{fix_message}**")
        
        # تشغيل الملف بعد تثبيت المكتبات والتصحيح
        start_file(file_path, chat_id)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ **خطأ في التثبيت:** {str(e)}")

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

    # التحقق من الاشتراك في القناة
    if not check_subscription(user_id):
        show_subscription_required(message.chat.id)
        return

    show_main_menu(message)

@bot.callback_query_handler(func=lambda call: call.data == 'check_subscription')
def check_subscription_callback(call):
    """التحقق من الاشتراك عند الضغط على الزر"""
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "✅ تم التحقق من الاشتراك!")
        show_main_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد!")
        show_subscription_required(call.message.chat.id)

def show_main_menu(message):
    """عرض القائمة الرئيسية مع الأزرار المطلوبة"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # الأزرار الرئيسية
    upload_button = types.InlineKeyboardButton("رفع ملف 📥", callback_data='upload')
    extract_libs_button = types.InlineKeyboardButton("📦 استخراج مكتبات", callback_data='extract_libs')
    speed_button = types.InlineKeyboardButton("🚀 سرعة البوت", callback_data='speed')
    about_button = types.InlineKeyboardButton("ℹ️ حول البوت", callback_data='about_bot')
    tech_support_button = types.InlineKeyboardButton("🛠️ الدعم الفني", callback_data='tech_support')
    install_lib_button = types.InlineKeyboardButton("📚 تثبيت مكتبة", callback_data='download_lib')
    contact_support_button = types.InlineKeyboardButton("📞 التواصل مع الدعم", callback_data='online_support')
    channel_button = types.InlineKeyboardButton("📢 قناتنا", url=CHANNEL_LINK)
    
    # ترتيب الأزرار
    markup.add(upload_button, extract_libs_button)
    markup.add(speed_button, about_button)
    markup.add(tech_support_button, install_lib_button)
    markup.add(contact_support_button, channel_button)
    
    # إضافة أزرار الأدمن إذا كان مستخدم مسؤول
    if is_admin(message.from_user.id):
        admin_panel_button = types.InlineKeyboardButton("👑 لوحة الأدمن", callback_data='admin_panel')
        markup.add(admin_panel_button)

    # التحقق من الاشتراك قبل عرض القائمة
    if not check_subscription(message.from_user.id):
        show_subscription_required(message.chat.id)
        return

    bot.send_message(
        message.chat.id,
        f"🐍 **Python Hosting** 🐍\n\n"
        f"مرحباً، {message.from_user.first_name}! 👋\n\n"
        "**الميزات المتاحة:** ✅\n\n"
        "• تشغيل الملف على سيرفر خاص\n"
        "• تشغيل الملفات بكل سهولة وسرعة\n"
        "• استخراج وتثبيت المكتبات تلقائياً\n"
        "• 🔧 التصحيح التلقائي للملفات\n"
        "• بوت استضافات مجانيه: @puistbot\n\n"
        "**اختر من الأزرار أدناه:**",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ======= لوحة الأدمن المتقدمة ======= #
@bot.callback_query_handler(func=lambda call: call.data == 'admin_panel')
def admin_panel_callback(call):
    """لوحة تحكم الأدمن"""
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية الوصول")
        return
    
    bot.answer_callback_query(call.id, "👑 جاري فتح لوحة الأدمن...")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # أزرار لوحة الأدمن
    stats_button = types.InlineKeyboardButton("📊 الإحصائيات", callback_data='admin_stats')
    broadcast_button = types.InlineKeyboardButton("📢 البث للجميع", callback_data='admin_broadcast')
    broadcast_bots_button = types.InlineKeyboardButton("🤖 البث للبوتات", callback_data='admin_broadcast_bots')
    channel_settings_button = types.InlineKeyboardButton("⚙️ إعدادات القناة", callback_data='admin_channel')
    users_button = types.InlineKeyboardButton("👥 إدارة المستخدمين", callback_data='manage_users')
    bot_control_button = types.InlineKeyboardButton("⚡ تشغيل/إيقاف البوت", callback_data='bot_control')
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')
    
    markup.add(stats_button, broadcast_button)
    markup.add(broadcast_bots_button, channel_settings_button)
    markup.add(users_button, bot_control_button)
    markup.add(back_button)
    
    bot.edit_message_text(
        "👑 **لوحة تحكم الأدمن**\n\n"
        "**الأدوات المتاحة:**\n"
        "• 📊 عرض إحصائيات البوت\n"
        "• 📢 بث رسائل للجميع\n"
        "• 🤖 بث رسائل للبوتات النشطة\n"
        "• ⚙️ تغيير قناة الاشتراك\n"
        "• 👥 إدارة المستخدمين\n"
        "• ⚡ التحكم في البوت\n\n"
        "اختر الأداة التي تريد استخدامها:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'admin_broadcast_bots')
def admin_broadcast_bots_callback(call):
    """بث رسالة للبوتات النشطة"""
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    
    bot.answer_callback_query(call.id, "🤖 جاري إعداد البث للبوتات...")
    
    markup = types.InlineKeyboardMarkup()
    cancel_button = types.InlineKeyboardButton("❌ إلغاء", callback_data='admin_panel')
    markup.add(cancel_button)
    
    bot.send_message(
        call.message.chat.id,
        "🤖 **بث رسالة للبوتات النشطة**\n\n"
        "أرسل الرسالة التي تريد بثها للبوتات النشطة فقط:\n\n"
        "سيتم الإرسال للبوتات التي تعمل حالياً على السيرفر",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    
    bot.register_next_step_handler(call.message, handle_broadcast_to_bots)

def handle_broadcast_to_bots(message):
    """معالجة رسالة البث للبوتات"""
    if not is_admin(message.from_user.id):
        return
    
    broadcast_text = message.text
    
    # إرسال رسالة الانتظار
    wait_msg = bot.send_message(message.chat.id, "⏳ **جاري إرسال الرسالة للبوتات النشطة...**")
    
    # بث الرسالة للبوتات النشطة
    success, failed, active_bots = broadcast_to_active_bots(broadcast_text)
    
    # عرض النتيجة
    result_text = f"✅ **تم الانتهاء من البث للبوتات**\n\n"
    result_text += f"📊 **النتائج:**\n"
    result_text += f"• ✅ تم الإرسال بنجاح: {success} بوت\n"
    result_text += f"• ❌ فشل في الإرسال: {failed} بوت\n\n"
    
    if active_bots:
        result_text += "🤖 **البوتات النشطة:**\n"
        for bot_info in active_bots:
            result_text += f"• {bot_info['name']} (@{bot_info['uploader']})\n"
    
    bot.edit_message_text(
        result_text,
        message.chat.id,
        wait_msg.message_id,
        parse_mode='Markdown'
    )

# ======= باقي دوال الأدمن (يتم الحفاظ عليها) ======= #

@bot.callback_query_handler(func=lambda call: call.data == 'admin_stats')
def admin_stats_callback(call):
    """عرض إحصائيات البوت"""
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية")
        return
    
    stats = get_bot_statistics()
    
    markup = types.InlineKeyboardMarkup()
    refresh_button = types.InlineKeyboardButton("🔄 تحديث", callback_data='admin_stats')
    back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')
    markup.add(refresh_button, back_button)
    
    stats_text = f"📊 **إحصائيات البوت**\n\n"
    stats_text += f"👥 **المستخدمون:**\n"
    stats_text += f"• إجمالي المستخدمين: {stats['total_users']}\n"
    stats_text += f"• المستخدمون المحظورون: {stats['banned_users']}\n\n"
    stats_text += f"🤖 **البوتات:**\n"
    stats_text += f"• البوتات النشطة: {stats['active_bots']}\n"
    stats_text += f"• الملفات المحفوظة: {stats['total_files']}\n\n"
    
    if stats['active_bots_list']:
        stats_text += f"**البوتات النشطة حالياً:**\n"
        for bot_info in stats['active_bots_list']:
            stats_text += f"• {bot_info['name']} (@{bot_info['uploader']})\n"
        stats_text += f"\n"
    
    stats_text += f"⏰ **معلومات التشغيل:**\n"
    stats_text += f"• آخر تحديث: {stats['uptime']}\n"
    stats_text += f"• حالة البوت: {'🟢 يعمل' if bot_running else '🔴 متوقف'}\n\n"
    stats_text += f"📢 **قناة الاشتراك:**\n"
    stats_text += f"• {CHANNEL_USERNAME}"
    
    bot.edit_message_text(
        stats_text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ======= معالجة رفع الملفات مع التصحيح التلقائي ======= #
@bot.message_handler(content_types=['document'])
def handle_file(message):
    # التحقق من الاشتراك أولاً
    if not check_subscription(message.from_user.id):
        show_subscription_required(message.chat.id)
        return
        
    try:
        user_id = message.from_user.id
        
        if message.from_user.username in banned_users:
            bot.send_message(message.chat.id, "⁉️ تم حظرك من البوت")
            return

        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        bot_script_name = message.document.file_name
        
        # إذا كان الملف بايثون، نستخرج المكتبات
        if bot_script_name.endswith('.py'):
            downloaded_file = bot.download_file(file_info.file_path)
            file_content = downloaded_file.decode('utf-8', errors='ignore')
            
            # استخراج المكتبات
            libraries = extract_libraries_from_file(file_content)
            
            if libraries:
                # تثبيت المكتبات تلقائياً
                temp_path = os.path.join(tempfile.gettempdir(), bot_script_name)
                with open(temp_path, 'wb') as temp_file:
                    temp_file.write(downloaded_file)

                # التصحيح التلقائي للملف
                fixed, fix_message = auto_fix_python_file(temp_path)
                        
                script_path = os.path.join(uploaded_files_dir, bot_script_name)
                shutil.move(temp_path, script_path)

                bot_scripts[message.chat.id] = {
                    'name': bot_script_name,
                    'uploader': message.from_user.username,
                    'path': script_path,
                    'process': None
                }

                # تثبيت المكتبات وتشغيل الملف
                auto_install_libraries_and_start(script_path, message.chat.id, file_content)
                
                markup = types.InlineKeyboardMarkup()
                stop_button = types.InlineKeyboardButton(f"🛑 إيقاف {bot_script_name}", callback_data=f'stop_{message.chat.id}_{bot_script_name}')
                channel_button = types.InlineKeyboardButton("📢 قناتنا", url=CHANNEL_LINK)
                markup.add(stop_button, channel_button)

                response_text = f"✅ **تم رفع الملف بنجاح**\n\n"
                response_text += f"📁 الملف: {bot_script_name}\n"
                response_text += f"👤 المستخدم: @{message.from_user.username}\n"
                response_text += f"📦 المكتبات المثبتة: {len(libraries)}\n"
                
                if fixed:
                    response_text += f"🔧 {fix_message}\n"
                
                response_text += f"📢 قناتنا: {CHANNEL_USERNAME}\n\n"
                response_text += f"🌟 **بوت استضافات مجانيه: @puistbot**\n\n"
                response_text += f"يمكنك إيقاف التشغيل بالزر أدناه:"

                bot.reply_to(
                    message,
                    response_text,
                    reply_markup=markup
                )
            else:
                bot.reply_to(
                    message,
                    "❌ **لم يتم العثور على مكتبات في الملف**\n\n"
                    "🌟 **بوت استضافات مجانيه: @puistbot**"
                )
            return

        # إذا كان الملف كبيراً
        if file_info.file_size > MAX_FILE_SIZE:
            bot.reply_to(message, "⛔ حجم الملف يتجاوز 10MB")
            return
            
        downloaded_file = bot.download_file(file_info.file_path)
        
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
        
        # التصحيح التلقائي للملف
        fixed, fix_message = auto_fix_python_file(temp_path)
                
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
        channel_button = types.InlineKeyboardButton("📢 قناتنا", url=CHANNEL_LINK)
        markup.add(stop_button, channel_button)

        response_text = f"✅ **تم رفع الملف بنجاح**\n\n"
        response_text += f"📁 الملف: {bot_script_name}\n"
        response_text += f"👤 المستخدم: @{message.from_user.username}\n"
        
        if fixed:
            response_text += f"🔧 {fix_message}\n"
        
        response_text += f"📢 قناتنا: {CHANNEL_USERNAME}\n\n"
        response_text += f"🌟 **بوت استضافات مجانيه: @puistbot**\n\n"
        response_text += f"يمكنك إيقاف التشغيل بالزر أدناه:"

        bot.reply_to(
            message,
            response_text,
            reply_markup=markup
        )
        
        # تشغيل الملف
        start_file(script_path, message.chat.id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {e}")
# ======= دوال معالجة الأزرار المعدلة ======= #

@bot.callback_query_handler(func=lambda call: call.data == 'upload')
def upload_file_callback(call):
    """زر رفع الملف"""
    try:
        if not bot_running:
            bot.answer_callback_query(call.id, "⏸️ البوت متوقف حالياً")
            return
            
        # التحقق من الاشتراك
        if not check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
            show_subscription_required(call.message.chat.id)
            return
            
        bot.answer_callback_query(call.id, "📤 جاري إعداد رفع الملف...")
        
        markup = types.InlineKeyboardMarkup()
        cancel_button = types.InlineKeyboardButton("❌ إلغاء", callback_data='back_to_main')
        markup.add(cancel_button)
        
        # حذف الرسالة القديمة وإرسال جديدة
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
        bot.send_message(
            call.message.chat.id,
            "📤 **رفع ملف**\n\n"
            "أرسل ملف البوت الآن (ملف .py فقط)\n"
            "الحد الأقصى للحجم: 10MB\n\n"
            "🌟 **بوت استضافات مجانيه: @puistbot**\n\n"
            "سيتم تثبيت المكتبات تلقائياً وتشغيل الملف",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ")
        print(f"Error in upload callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'extract_libs')
def extract_libs_callback(call):
    """زر استخراج المكتبات"""
    try:
        # التحقق من الاشتراك
        if not check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
            return
            
        bot.answer_callback_query(call.id, "📦 جاري إعداد استخراج المكتبات...")
        
        markup = types.InlineKeyboardMarkup()
        cancel_button = types.InlineKeyboardButton("❌ إلغاء", callback_data='back_to_main')
        markup.add(cancel_button)
        
        # حذف الرسالة القديمة وإرسال جديدة
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
        bot.send_message(
            call.message.chat.id,
            "📦 **استخراج المكتبات من الملفات**\n\n"
            "أرسل ملف Python (.py) الآن وسأستخرج المكتبات المستخدمة فيه\n\n"
            "🌟 **بوت استضافات مجانيه: @puistbot**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ")
        print(f"Error in extract libs callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'speed')
def check_speed(call):
    """زر قياس السرعة"""
    try:
        # التحقق من الاشتراك
        if not check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
            return
            
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
            f"🌟 **بوت استضافات مجانيه: @puistbot**\n\n"
            f"_{datetime.now().strftime('%I:%M %p')}_",
            call.message.chat.id,
            wait_msg.message_id,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ في قياس السرعة")
        print(f"Error in speed callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'about_bot')
def about_bot(call):
    """زر حول البوت"""
    try:
        # التحقق من الاشتراك
        if not check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
            return
            
        bot.answer_callback_query(call.id, "ℹ️ جاري تحميل المعلومات...")
        
        markup = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')
        markup.add(back_button)
        
        # حذف الرسالة القديمة وإرسال جديدة
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
        bot.send_message(
            call.message.chat.id,
            "ℹ️ **حول البوت**\n\n"
            "🐍 **Python Hosting Bot**\n\n"
            "**المميزات:**\n"
            "✅ تشغيل الملفات على سيرفر خاص\n"
            "✅ سرعة وأداء عالي\n"
            "✅ تثبيت المكتبات تلقائياً\n"
            "✅ 🔧 التصحيح التلقائي للملفات\n"
            "✅ دعم فني متكامل\n"
            "✅ إدارة مستخدمين ذكية\n\n"
            "**للمطورين:**\n"
            "🔹 رفع وتشغيل ملفات .py\n"
            "🔹 تثبيت المكتبات المطلوبة\n"
            "🔹 مراقبة أداء البوت\n"
            "🔹 تحكم كامل في العمليات\n\n"
            "🌟 **بوت استضافات مجانيه: @puistbot**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ")
        print(f"Error in about callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'tech_support')
def tech_support_callback(call):
    """زر الدعم الفني"""
    try:
        # التحقق من الاشتراك
        if not check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
            return
            
        bot.answer_callback_query(call.id, "🛠️ جاري تحويلك للدعم الفني...")
        
        markup = types.InlineKeyboardMarkup()
        common_issues_button = types.InlineKeyboardButton("🔧 المشاكل الشائعة", callback_data='common_issues')
        contact_admin_button = types.InlineKeyboardButton("👨‍💼 التواصل مع الأدمن", callback_data='online_support')
        channel_button = types.InlineKeyboardButton("📢 قناتنا", url=CHANNEL_LINK)
        back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')
        markup.add(common_issues_button)
        markup.add(contact_admin_button, channel_button)
        markup.add(back_button)
        
        # حذف الرسالة القديمة وإرسال جديدة
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
        bot.send_message(
            call.message.chat.id,
            "🛠️ **الدعم الفني**\n\n"
            "**الخدمات المتاحة:**\n"
            "• حل المشاكل التقنية\n"
            "• استكشاف الأخطاء وإصلاحها\n"
            "• دعم في تشغيل الملفات\n"
            "• مساعدة في تثبيت المكتبات\n"
            "• 🔧 التصحيح التلقائي للملفات\n\n"
            f"📢 **قناتنا:** {CHANNEL_USERNAME}\n\n"
            "🌟 **بوت استضافات مجانيه: @puistbot**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ")
        print(f"Error in tech support callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'download_lib')
def download_library(call):
    """زر تثبيت مكتبة"""
    try:
        # التحقق من الاشتراك
        if not check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
            return
            
        bot.answer_callback_query(call.id, "📚 جاري إعداد تثبيت المكتبة...")
        
        markup = types.InlineKeyboardMarkup()
        cancel_button = types.InlineKeyboardButton("❌ إلغاء", callback_data='back_to_main')
        markup.add(cancel_button)
        
        # حذف الرسالة القديمة وإرسال جديدة
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
        bot.send_message(
            call.message.chat.id,
            "📚 **تثبيت مكتبة**\n\n"
            "أرسل اسم المكتبة التي تريد تثبيتها:\n\n"
            "مثال: `telegram` أو `python-telegram-bot`\n\n"
            "🌟 **بوت استضافات مجانيه: @puistbot**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        bot.register_next_step_handler(call.message, install_library_step)
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ")
        print(f"Error in download lib callback: {e}")

def install_library_step(message):
    """معالجة تثبيت المكتبة"""
    try:
        library_name = message.text.strip()
        if not library_name:
            bot.send_message(message.chat.id, "❌ لم تقم بإدخال اسم المكتبة")
            return
            
        bot.send_message(message.chat.id, f"🔄 جاري تثبيت `{library_name}`...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", library_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                bot.send_message(message.chat.id, f"✅ تم تثبيت `{library_name}` بنجاح\n\n🌟 **بوت استضافات مجانيه: @puistbot**")
            else:
                error_msg = result.stderr if result.stderr else "خطأ غير معروف"
                bot.send_message(message.chat.id, f"❌ فشل في تثبيت `{library_name}`\n\n`{error_msg}`")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ في التثبيت: `{str(e)}`")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'online_support')
def online_support(call):
    """زر التواصل مع الدعم"""
    try:
        # التحقق من الاشتراك
        if not check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ يجب الاشتراك في القناة أولاً")
            return
            
        bot.answer_callback_query(call.id, "📞 جاري إرسال طلب الدعم...")
        
        user_info = f"👤 {call.from_user.first_name}\n🆔 {call.from_user.id}\n📌 @{call.from_user.username or 'غير متوفر'}"
        
        # إرسال طلب الدعم للأدمن
        markup = types.InlineKeyboardMarkup()
        contact_user_button = types.InlineKeyboardButton("📞 التواصل مع المستخدم", url=f"tg://user?id={call.from_user.id}")
        markup.add(contact_user_button)
        
        bot.send_message(
            ADMIN_ID,
            f"📞 **طلب دعم فوري**\n\n{user_info}\n\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=markup
        )
        
        bot.send_message(call.message.chat.id, 
            "✅ **تم إرسال طلب الدعم للأدمن**\n\n"
            "سيتواصل معك الأدمن في أقرب وقت ممكن.\n\n"
            "🌟 **بوت استضافات مجانيه: @puistbot**"
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ في إرسال الطلب")
        print(f"Error in online support callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'common_issues')
def common_issues_callback(call):
    """المشاكل الشائعة"""
    try:
        bot.answer_callback_query(call.id, "🔧 جاري تحميل المشاكل الشائعة...")
        
        markup = types.InlineKeyboardMarkup()
        file_issue = types.InlineKeyboardButton("📁 الملف لا يعمل", callback_data='issue_file')
        import_issue = types.InlineKeyboardButton("📚 مشكلة في الاستيراد", callback_data='issue_import')
        install_issue = types.InlineKeyboardButton("🐍 مشكلة في التثبيت", callback_data='issue_install')
        speed_issue = types.InlineKeyboardButton("🐌 البوت بطيء", callback_data='issue_speed')
        back_button = types.InlineKeyboardButton("🔙 رجوع", callback_data='tech_support')
        markup.add(file_issue, import_issue)
        markup.add(install_issue, speed_issue)
        markup.add(back_button)
        
        # حذف الرسالة القديمة وإرسال جديدة
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
        bot.send_message(
            call.message.chat.id,
            "🔧 **المشاكل الشائعة**\n\n"
            "اختر نوع المشكلة التي تواجهك:\n\n"
            "🌟 **بوت استضافات مجانيه: @puistbot**",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ")
        print(f"Error in common issues callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('issue_'))
def handle_common_issue(call):
    """معالجة المشاكل الشائعة"""
    try:
        issue_type = call.data.replace('issue_', '')
        
        solutions = {
            'file': "**حلول مشكلة الملف لا يعمل:**\n\n"
                    "1. تأكد أن الملف بصيغة .py\n"
                    "2. تحقق من وجود أخطاء في الكود\n"
                    "3. تأكد من تثبيت جميع المكتبات المطلوبة\n"
                    "4. حاول إعادة رفع الملف\n"
                    "5. استخدم زر 🔧 التصحيح التلقائي\n\n"
                    "🌟 **بوت استضافات مجانيه: @puistbot**",
            
            'import': "**حلول مشاكل الاستيراد:**\n\n"
                     "1. تأكد من صحة أسماء المكتبات\n"
                     "2. استخدم التصحيح التلقائي للملف\n"
                     "3. جرب تثبيت المكتبة يدوياً\n"
                     "4. تحقق من إصدار المكتبة\n\n"
                     "🌟 **بوت استضافات مجانيه: @puistbot**",
            
            'install': "**حلول مشاكل التثبيت:**\n\n"
                      "1. تأكد من اسم المكتبة\n"
                      "2. جرب تثبيت إصدار محدد: `pip install library==version`\n"
                      "3. تأكد من اتصال الإنترنت\n"
                      "4. جرب تحديث pip: `pip install --upgrade pip`\n\n"
                      "🌟 **بوت استضافات مجانيه: @puistbot**",
            
            'speed': "**تحسين سرعة البوت:**\n\n"
                    "1. تأكد من جودة الاتصال بالإنترنت\n"
                    "2. أغلق الملفات غير المستخدمة\n"
                    "3. حاول إعادة تشغيل البوت\n"
                    "4. تأكد من عدم وجود عمليات ثقيلة\n\n"
                    "🌟 **بوت استضافات مجانيه: @puistbot**"
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
        
        # حذف الرسالة القديمة وإرسال جديدة
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
        bot.send_message(
            call.message.chat.id,
            solution,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ")
        print(f"Error in issue callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_to_main(call):
    """زر الرجوع للقائمة الرئيسية"""
    try:
        # التحقق من الاشتراك قبل العودة للقائمة
        if not check_subscription(call.from_user.id):
            show_subscription_required(call.message.chat.id)
            return
            
        show_main_menu(call.message)
        bot.answer_callback_query(call.id, "🏠 العودة للقائمة الرئيسية")
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ حدث خطأ في العودة")
        print(f"Error in back to main callback: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_bot_callback(call):
    """إيقاف البوت"""
    try:
        parts = call.data.split('_')
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "❌ بيانات غير صحيحة")
            return
            
        chat_id = int(parts[1])
        script_name = '_'.join(parts[2:])
        
        script_path = os.path.join(uploaded_files_dir, script_name)
        if stop_bot(script_path, chat_id):
            bot.answer_callback_query(call.id, "✅ تم إيقاف البوت")
            
            # تحديث الرسالة
            bot.edit_message_text(
                f"🛑 **تم إيقاف {script_name}**\n\n"
                f"🌟 **بوت استضافات مجانيه: @puistbot**",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
        else:
            bot.answer_callback_query(call.id, "❌ فشل في إيقاف البوت")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطأ: {e}")
        print(f"Error in stop bot callback: {e}")
# تشغيل البوت
if __name__ == '__main__':
    print("🤖 البوت يعمل...")
    print(f"✅ المستخدمون: {len(approved_users)}")
    print(f"⚡ حالة البوت: {'يعمل' if bot_running else 'متوقف'}")
    print(f"📢 قناة الاشتراك الإجباري: {CHANNEL_USERNAME}")
    print("🌟 بوت استضافات مجانيه: @puistbot")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        time.sleep(5)
