import os
import logging
import asyncio
import aiohttp
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# 🔑 إعدادات بوت الإدارة - التوكن الجديد
ADMIN_BOT_TOKEN = "8205170895:AAE9D0BAnGWE3_5FyEtY08FP8bivzcv8XRY"
MAIN_BOT_TOKEN = "8122538449:AAGE9NIO18L6OqF5DZlQxsIK6x7LdHDJwmA"

# 👥 المسؤولون - ضع رقمك هنا
ADMINS = [6096879850]  # استبدل برقمك الصحيح

class SmartAIAdminBot:
    def __init__(self):
        self.bot_settings = self.load_settings()
        self.setup_commands()
        logging.info("🤖 بوت الإدارة الذكي تم تهيئته")
    
    def setup_commands(self):
        """إعداد الأوامر التي يفهمها الذكاء الاصطناعي"""
        self.available_commands = {
            "add_subscription": {
                "keywords": ["اشتراك اجباري", "إجباري", "اشتراك", "subscription", "شغل اشتراك"],
                "description": "تفعيل الاشتراك الإجباري",
                "function": self.enable_subscription
            },
            "remove_subscription": {
                "keywords": ["إلغاء الاشتراك", "إلغاء إجباري", "إلغاء اشتراك", "اقفل اشتراك"],
                "description": "إلغاء الاشتراك الإجباري",
                "function": self.disable_subscription
            },
            "add_donation": {
                "keywords": ["تبرع", "دعم", "donation", "تبرعات", "رابط تبرع"],
                "description": "إضافة رابط التبرع",
                "function": self.add_donation_link
            },
            "add_trending_coin": {
                "keywords": ["ضيف عملة", "إضافة عملة", "عملة جديدة", "add coin", "زود عملة"],
                "description": "إضافة عملة إلى القائمة الترند",
                "function": self.add_trending_coin
            },
            "remove_coin": {
                "keywords": ["شيل عملة", "احذف عملة", "حذف عملة", "remove coin", "مسح عملة"],
                "description": "حذف عملة من القائمة",
                "function": self.remove_trending_coin
            },
            "change_welcome": {
                "keywords": ["عدل ترحيب", "تغيير ترحيب", "رسالة ترحيب", "welcome", "غير ترحيب"],
                "description": "تغيير رسالة الترحيب",
                "function": self.change_welcome_message
            },
            "broadcast": {
                "keywords": ["اذاعة", "بث", "رسالة جماعية", "broadcast", "أعلان"],
                "description": "إرسال رسالة جماعية",
                "function": self.prepare_broadcast
            },
            "show_settings": {
                "keywords": ["عرض الإعدادات", "الإعدادات", "settings", "الاعدادات"],
                "description": "عرض الإعدادات الحالية",
                "function": self.show_settings
            },
            "add_button": {
                "keywords": ["زر جديد", "إضافة زر", "ضيف زر", "button", "رابط"],
                "description": "إضافة زر جديد في الواجهة",
                "function": self.add_custom_button
            }
        }
    
    def load_settings(self):
        """تحميل الإعدادات من ملف أو إنشاء إعدادات افتراضية"""
        try:
            return {
                "welcome_message": "🌟 مرحباً بك في بوت الأسعار المتقدم!",
                "subscription_required": False,
                "subscription_channel": "@zforexms",
                "trending_coins": ["BTC", "ETH", "SOL", "TON", "XRP", "ADA", "DOT", "MATIC"],
                "donation_link": "",
                "broadcast_message": "",
                "custom_buttons": [],
                "main_bot_token": MAIN_BOT_TOKEN
            }
        except Exception as e:
            logging.error(f"خطأ في تحميل الإعدادات: {e}")
            return self.load_settings()
    
    def save_settings(self, settings=None):
        """حفظ الإعدادات"""
        if settings:
            self.bot_settings = settings
        logging.info("✅ تم حفظ الإعدادات")
    
    async def analyze_command(self, user_message):
        """تحليل الأمر باستخدام الذكاء الاصطناعي المبسط"""
        message_lower = user_message.lower()
        
        for command, info in self.available_commands.items():
            for keyword in info['keywords']:
                if keyword in message_lower:
                    return {
                        "command": command,
                        "parameters": self.extract_parameters(user_message, command),
                        "response": f"🎯 تم التعرف على الأمر: {keyword}",
                        "action_required": True
                    }
        
        return {
            "command": "unknown",
            "response": "🤔 لم أفهم الأمر بوضوح. جرب:\n• 'ضيف عملة BTC'\n• 'شغل الاشتراك الإجباري'\n• 'عدل ترحيب مرحباً'\n• 'عرض الإعدادات'",
            "action_required": False
        }
    
    def extract_parameters(self, message, command):
        """استخراج المعلمات من الرسالة"""
        params = {}
        
        if command == "add_trending_coin":
            # استخراج رموز العملات
            coins = re.findall(r'[A-Z]{2,5}', message.upper())
            params['coins'] = [coin for coin in coins if coin not in ['ADD', 'REMOVE', 'COIN', 'SHOW', 'WORK']]
        
        elif command == "add_donation":
            # استخراج رابط التبرع
            links = re.findall(r'https?://[^\s]+', message)
            if links:
                params['donation_link'] = links[0]
        
        elif command == "change_welcome":
            # استخراج نص الترحيب
            welcome_text = message.replace('ترحيب', '').replace('welcome', '').replace('عدل', '').replace('تغيير', '').strip()
            params['welcome_message'] = welcome_text
        
        elif command == "broadcast":
            # استخراج نص البث
            broadcast_text = message.replace('اذاعة', '').replace('بث', '').replace('اعمل', '').strip()
            params['broadcast_text'] = broadcast_text
        
        elif command == "add_button":
            # استخراج بيانات الزر
            button_parts = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', message)
            if button_parts:
                params['button_text'] = button_parts[0][0]
                params['button_url'] = button_parts[0][1]
        
        return params
    
    async def execute_command(self, command, parameters):
        """تنفيذ الأمر المطلوب"""
        try:
            if command in self.available_commands:
                result = await self.available_commands[command]['function'](parameters)
                
                # تحديث بوت العملات الرئيسي
                await self.update_main_bot()
                
                return result
            return "❌ الأمر غير معروف"
        except Exception as e:
            logging.error(f"خطأ في التنفيذ: {e}")
            return f"❌ خطأ في التنفيذ: {str(e)}"
    
    async def enable_subscription(self, params):
        """تفعيل الاشتراك الإجباري"""
        self.bot_settings["subscription_required"] = True
        self.save_settings()
        return "✅ تم تفعيل الاشتراك الإجباري بنجاح\n📢 سيطلب من المستخدمين الاشتراك في القناة قبل الاستخدام"
    
    async def disable_subscription(self, params):
        """إلغاء الاشتراك الإجباري"""
        self.bot_settings["subscription_required"] = False
        self.save_settings()
        return "✅ تم إلغاء الاشتراك الإجباري بنجاح\n👋 يمكن للمستخدمين استخدام البوت مباشرة"
    
    async def add_donation_link(self, params):
        """إضافة رابط التبرع"""
        if 'donation_link' in params:
            self.bot_settings["donation_link"] = params['donation_link']
            self.save_settings()
            return f"✅ تم إضافة رابط التبرع بنجاح:\n{params['donation_link']}"
        return "❌ لم يتم تقديم رابط التبرع\n📝 مثال: 'ضيف رابط تبرع https://paypal.com/donate'"
    
    async def add_trending_coin(self, params):
        """إضافة عملة ترند"""
        if 'coins' in params and params['coins']:
            new_coins = []
            for coin in params['coins']:
                if coin not in self.bot_settings["trending_coins"]:
                    self.bot_settings["trending_coins"].append(coin)
                    new_coins.append(coin)
            
            self.save_settings()
            if new_coins:
                return f"✅ تمت إضافة العملات بنجاح:\n{', '.join(new_coins)}\n\n📊 العملات الحالية: {', '.join(self.bot_settings['trending_coins'])}"
            else:
                return f"ℹ️ العملات موجودة بالفعل في القائمة\n📊 العملات الحالية: {', '.join(self.bot_settings['trending_coins'])}"
        return "❌ لم يتم تحديد عملات للإضافة\n📝 مثال: 'ضيف عملة BTC ETH'"
    
    async def remove_trending_coin(self, params):
        """حذف عملة ترند"""
        if 'coins' in params and params['coins']:
            removed_coins = []
            for coin in params['coins']:
                if coin in self.bot_settings["trending_coins"]:
                    self.bot_settings["trending_coins"].remove(coin)
                    removed_coins.append(coin)
            
            self.save_settings()
            if removed_coins:
                return f"✅ تم حذف العملات بنجاح:\n{', '.join(removed_coins)}\n\n📊 العملات المتبقية: {', '.join(self.bot_settings['trending_coins'])}"
            else:
                return f"❌ العملات غير موجودة في القائمة\n📊 العملات الحالية: {', '.join(self.bot_settings['trending_coins'])}"
        return "❌ لم يتم تحديد عملات للحذف\n📝 مثال: 'شيل عملة BTC'"
    
    async def change_welcome_message(self, params):
        """تغيير رسالة الترحيب"""
        if 'welcome_message' in params and params['welcome_message']:
            self.bot_settings["welcome_message"] = params['welcome_message']
            self.save_settings()
            return f"✅ تم تحديث رسالة الترحيب بنجاح:\n\n{params['welcome_message']}"
        return "❌ لم يتم تقديم نص الترحيب\n📝 مثال: 'عدل ترحيب أهلاً وسهلاً بكم'"
    
    async def prepare_broadcast(self, params):
        """تحضير رسالة البث"""
        if 'broadcast_text' in params and params['broadcast_text']:
            self.bot_settings["broadcast_message"] = params['broadcast_text']
            self.save_settings()
            return f"✅ تم حفظ رسالة البث بنجاح\n\n📢 الرسالة:\n{params['broadcast_text']}\n\n🚀 يمكنك إرسالها الآن من خلال خيار البث"
        return "❌ لم يتم تقديم نص البث\n📝 مثال: 'اعمل اذاعة مرحباً بالجدد'"
    
    async def show_settings(self, params):
        """عرض الإعدادات الحالية"""
        settings = self.bot_settings
        response = "⚙️ **الإعدادات الحالية:**\n\n"
        response += f"📝 **الترحيب:** {settings['welcome_message']}\n"
        response += f"🔔 **الاشتراك الإجباري:** {'✅ مفعل' if settings['subscription_required'] else '❌ معطل'}\n"
        response += f"📢 **قناة الاشتراك:** {settings['subscription_channel']}\n"
        response += f"💰 **رابط التبرع:** {settings['donation_link'] or '❌ غير مضاف'}\n"
        response += f"📊 **العملات الترند:** {', '.join(settings['trending_coins'])}\n"
        response += f"📢 **رسالة البث:** {settings['broadcast_message'][:50] + '...' if settings['broadcast_message'] else '❌ لا توجد'}\n"
        response += f"🔗 **الأزرار المخصصة:** {len(settings['custom_buttons'])} زر"
        return response
    
    async def add_custom_button(self, params):
        """إضافة زر مخصص"""
        if 'button_text' in params and 'button_url' in params:
            new_button = {
                "text": params['button_text'],
                "url": params['button_url']
            }
            self.bot_settings["custom_buttons"].append(new_button)
            self.save_settings()
            return f"✅ تم إضافة الزر بنجاح:\n📝 النص: {params['button_text']}\n🔗 الرابط: {params['button_url']}"
        return "❌ بيانات الزر غير مكتملة\n📝 مثال: 'ضيف زر [قناتنا](https://t.me/zforexms)'"
    
    async def update_main_bot(self):
        """تحديث بوت العملات الرئيسي بالإعدادات الجديدة"""
        try:
            logging.info("🔄 جاري تحديث إعدادات البوت الرئيسي...")
            # هنا يمكن إضافة كود لإرسال الإعدادات للبوت الرئيسي
            return True
        except Exception as e:
            logging.error(f"❌ خطأ في تحديث البوت الرئيسي: {e}")
            return False

# 📱 Handlers للبوت
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسائل المسؤول"""
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى لوحة الإدارة")
        return
    
    user_message = update.message.text
    
    if not context.bot_data.get('admin_bot'):
        context.bot_data['admin_bot'] = SmartAIAdminBot()
    
    admin_bot = context.bot_data['admin_bot']
    
    # رسالة تحميل
    loading_msg = await update.message.reply_text("🤔 جاري تحليل طلبك...")
    
    try:
        # تحليل الأمر
        ai_analysis = await admin_bot.analyze_command(user_message)
        
        if ai_analysis['action_required']:
            # تنفيذ الأمر
            result = await admin_bot.execute_command(
                ai_analysis['command'], 
                ai_analysis['parameters']
            )
            response_message = f"{ai_analysis['response']}\n\n{result}"
        else:
            response_message = ai_analysis['response']
        
        await loading_msg.edit_text(response_message, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"خطأ في معالجة الرسالة: {e}")
        await loading_msg.edit_text("❌ حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى.")

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء بوت الإدارة"""
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى لوحة الإدارة")
        return
    
    welcome_text = """
🤖 **بوت الإدارة الذكي - الإصدار الجديد**

🎯 **متصل بنجاح مع بوت العملات الرئيسي**

🚀 **يمكنك التحدث معي بشكل طبيعي:**

🔹 **إدارة الاشتراك الإجباري**
• "شغل الاشتراك الإجباري"
• "إلغاء الاشتراك الإجباري"

🔹 **إدارة العملات الترند**  
• "ضيف عملة BTC ETH"
• "شيل عملة SOL"
• "عرض العملات"

🔹 **تخصيص البوت**
• "عدل ترحيب أهلاً وسهلاً"
• "ضيف رابط تبرع https://..."
• "ضيف زر [قناتنا](https://t.me/...)"

🔹 **نظام البث**
• "اعمل اذاعة مرحباً بالجميع"

🔹 **عرض الإعدادات**
• "عرض الإعدادات"

**💬 تكلم معي بشكل طبيعي وسأفهم طلبك!**
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 تحديث الإعدادات", callback_data="refresh_settings")],
        [InlineKeyboardButton("📊 عرض الإعدادات", callback_data="show_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMINS:
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول")
        return
    
    data = query.data
    
    if not context.bot_data.get('admin_bot'):
        context.bot_data['admin_bot'] = SmartAIAdminBot()
    
    admin_bot = context.bot_data['admin_bot']
    
    if data == "show_settings":
        settings_text = await admin_bot.show_settings({})
        await query.edit_message_text(settings_text, parse_mode='Markdown')
    
    elif data == "refresh_settings":
        await query.edit_message_text("✅ تم تحديث الإعدادات بنجاح")

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # إعدادات التسجيل
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    logging.info("🚀 بدء تشغيل بوت الإدارة الذكي...")
    
    try:
        # إنشاء تطبيق البوت
        application = Application.builder().token(ADMIN_BOT_TOKEN).build()
        
        # إضافة handlers
        application.add_handler(CommandHandler("start", admin_start))
        application.add_handler(CommandHandler("admin", admin_start))
        application.add_handler(CommandHandler("settings", admin_start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            handle_admin_message
        ))
        
        # تشغيل البوت
        logging.info(f"🤖 بوت الإدارة الذكي يعمل الآن!")
        logging.info(f"👤 المسؤولون: {ADMINS}")
        logging.info(f"🔗 متصل ببوت العملات: {MAIN_BOT_TOKEN[:10]}...")
        
        application.run_polling()
        
    except Exception as e:
        logging.error(f"❌ خطأ في تشغيل البوت: {e}")

if __name__ == '__main__':
    main()
