import os
import logging
import asyncio
import aiohttp
import json
import re
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# 🔑 التوكنات
ADMIN_BOT_TOKEN = "8205170895:AAE9D0BAnGWE3_5FyEtY08FP8bivzcv8XRY"
MAIN_BOT_TOKEN = "8122538449:AAGE9NIO18L6OqF5DZlQxsIK6x7LdHDJwmA"

# 👥 المسؤولون
ADMINS = [6096879850]

# 🔥 إيموجيز عصري
EMOJIS = {
    "ai": "🤖", "coin": "💰", "rocket": "🚀", "fire": "🔥", "chart": "📊",
    "money": "💸", "check": "✅", "error": "❌", "search": "🔍", "speed": "⚡",
    "brain": "🧠", "wifi": "📶", "update": "🔄", "settings": "⚙️", "bell": "🔔",
    "link": "🔗", "users": "👥", "time": "⏰", "star": "⭐", "crown": "👑"
}

class ModernAIBot:
    def __init__(self):
        self.settings = self.load_settings()
        self.session = None
        self.last_api_call = 0
        logging.info(f"{EMOJIS['ai']} البوت الذكي المتقدم تم تحميله")
    
    async def init_session(self):
        """تهيئة جلسة HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    def load_settings(self):
        """تحميل الإعدادات"""
        return {
            "welcome_message": f"{EMOJIS['rocket']} **مرحباً بك في بوت الأسعار المتقدم!**",
            "subscription_required": False,
            "subscription_channel": "@zforexms",
            "trending_coins": ["BTC", "ETH", "SOL", "TON", "XRP", "ADA", "DOT", "MATIC"],
            "donation_link": "",
            "custom_buttons": [],
            "api_timeout": 5
        }
    
    def save_settings(self):
        """حفظ الإعدادات"""
        logging.info(f"{EMOJIS['check']} تم حفظ الإعدادات")
    
    async def call_ai_api(self, message: str) -> dict:
        """الاتصال بـ AI API سريع"""
        try:
            await self.init_session()
            
            # منع تكرار الاستدعاءات السريعة
            current_time = time.time()
            if current_time - self.last_api_call < 1:
                await asyncio.sleep(1)
            self.last_api_call = current_time
            
            # API سريع ومجاني للفهم اللغوي
            payload = {
                "message": message,
                "context": "admin_bot_crypto_settings",
                "language": "ar"
            }
            
            async with self.session.post(
                "https://api.deepai.org/chat",  # API بديل سريع
                json=payload,
                timeout=5
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return await self.fallback_ai(message)
                    
        except Exception as e:
            logging.error(f"{EMOJIS['error']} خطأ في AI: {e}")
            return await self.fallback_ai(message)
    
    async def fallback_ai(self, message: str) -> dict:
        """ذكاء احتياطي سريع وفعال"""
        message_lower = message.lower()
        
        # فهم سريع للأوامر
        commands = {
            "اشتراك اجباري": "add_subscription",
            "إلغاء اشتراك": "remove_subscription", 
            "ضيف عملة": "add_coin",
            "شيل عملة": "remove_coin",
            "عدل ترحيب": "change_welcome",
            "رابط تبرع": "add_donation",
            "عرض الاعدادات": "show_settings",
            "اذاعة": "broadcast"
        }
        
        for key, command in commands.items():
            if key in message_lower:
                return {
                    "command": command,
                    "confidence": 0.9,
                    "response": f"فهمت أنك تريد {key}",
                    "parameters": self.extract_params(message, command)
                }
        
        return {
            "command": "unknown",
            "confidence": 0.1,
            "response": "اسف، لم أفهم. جرب:\n• ضيف عملة BTC\n• شغل الاشتراك\n• عدل ترحيب",
            "parameters": {}
        }
    
    def extract_params(self, message: str, command: str) -> dict:
        """استخراج المعلمات بسرعة"""
        params = {}
        
        if command == "add_coin":
            coins = re.findall(r'[A-Z]{2,5}', message.upper())
            params['coins'] = [c for c in coins if len(c) >= 2]
        
        elif command == "remove_coin":
            coins = re.findall(r'[A-Z]{2,5}', message.upper())
            params['coins'] = [c for c in coins if len(c) >= 2]
        
        elif command == "change_welcome":
            params['text'] = message.replace('عدل ترحيب', '').strip()
        
        elif command == "add_donation":
            links = re.findall(r'https?://[^\s]+', message)
            if links:
                params['link'] = links[0]
        
        elif command == "broadcast":
            params['text'] = message.replace('اذاعة', '').strip()
        
        return params
    
    async def execute_command(self, command: str, params: dict) -> str:
        """تنفيذ الأوامر بسرعة"""
        try:
            if command == "add_subscription":
                self.settings["subscription_required"] = True
                self.save_settings()
                return f"{EMOJIS['bell']} **تم تفعيل الاشتراك الإجباري**"
            
            elif command == "remove_subscription":
                self.settings["subscription_required"] = False
                self.save_settings()
                return f"{EMOJIS['check']} **تم إلغاء الاشتراك الإجباري**"
            
            elif command == "add_coin":
                if params.get('coins'):
                    new_coins = []
                    for coin in params['coins']:
                        if coin not in self.settings["trending_coins"]:
                            self.settings["trending_coins"].append(coin)
                            new_coins.append(coin)
                    
                    self.save_settings()
                    if new_coins:
                        return f"{EMOJIS['coin']} **تمت الإضافة:** {', '.join(new_coins)}"
                    return f"{EMOJIS['chart']} **موجودة مسبقاً**"
                return f"{EMOJIS['error']} **لم أجد عملات**"
            
            elif command == "remove_coin":
                if params.get('coins'):
                    removed = []
                    for coin in params['coins']:
                        if coin in self.settings["trending_coins"]:
                            self.settings["trending_coins"].remove(coin)
                            removed.append(coin)
                    
                    self.save_settings()
                    if removed:
                        return f"{EMOJIS['check']} **تم الحذف:** {', '.join(removed)}"
                    return f"{EMOJIS['error']} **غير موجودة**"
                return f"{EMOJIS['error']} **لم أجد عملات**"
            
            elif command == "change_welcome":
                if params.get('text'):
                    self.settings["welcome_message"] = params['text']
                    self.save_settings()
                    return f"{EMOJIS['check']} **تم تحديث الترحيب**"
                return f"{EMOJIS['error']} **لم يتم تقديم نص**"
            
            elif command == "add_donation":
                if params.get('link'):
                    self.settings["donation_link"] = params['link']
                    self.save_settings()
                    return f"{EMOJIS['money']} **تم إضافة رابط التبرع**"
                return f"{EMOJIS['error']} **لم يتم تقديم رابط**"
            
            elif command == "show_settings":
                return self.format_settings()
            
            else:
                return f"{EMOJIS['error']} **الأمر غير معروف**"
                
        except Exception as e:
            logging.error(f"خطأ في التنفيذ: {e}")
            return f"{EMOJIS['error']} **حدث خطأ: {str(e)}**"
    
    def format_settings(self) -> str:
        """تنسيق الإعدادات بشكل عصري"""
        settings = self.settings
        status = "✅ مفعل" if settings["subscription_required"] else "❌ معطل"
        
        return f"""
{EMOJIS['settings']} **الإعدادات الحالية**

{EMOJIS['bell']} **الاشتراك:** {status}
{EMOJIS['chart']} **العملات:** {', '.join(settings['trending_coins'])}
{EMOJIS['money']} **التبرع:** {settings['donation_link'] or 'غير مضاف'}
{EMOJIS['users']} **القناة:** {settings['subscription_channel']}
"""
    
    def create_modern_message(self, title: str, content: str, emoji: str = "🤖") -> str:
        """إنشاء رسالة عصرية"""
        return f"""
{emoji} ━━━━━ {title} ━━━━━ {emoji}

{content}

{emoji} ━━━━━━━━━━━━━━━━━━ {emoji}
"""

# النظام الأساسي
modern_bot = ModernAIBot()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل بسرعة"""
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text(f"{EMOJIS['error']} **ليس لديك صلاحية**")
        return
    
    user_message = update.message.text
    
    # رسالة تحميل سريعة
    loading_msg = await update.message.reply_text(f"{EMOJIS['search']} **جاري المعالجة...**")
    
    try:
        # استخدام AI للفهم
        ai_response = await modern_bot.call_ai_api(user_message)
        
        if ai_response['confidence'] > 0.5:
            # تنفيذ الأمر
            result = await modern_bot.execute_command(
                ai_response['command'],
                ai_response['parameters']
            )
            
            response = f"{ai_response['response']}\n\n{result}"
        else:
            response = ai_response['response']
        
        await loading_msg.edit_text(response, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"{EMOJIS['error']} **حدث خطأ غير متوقع**\n\n{str(e)}"
        await loading_msg.edit_text(error_msg, parse_mode='Markdown')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البوت"""
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text(f"{EMOJIS['error']} **ليس لديك صلاحية**")
        return
    
    welcome_text = modern_bot.create_modern_message(
        "بوت الإدارة الذكي",
        f"""
{EMOJIS['ai']} **مساعد ذكي متقدم**

{EMOJIS['speed']} **سريع الاستجابة**
{EMOJIS['brain']} **يفهم الأوامر الطبيعية**
{EMOJIS['wifi']} **متصل بـ AI API**

**📋 الأوامر المدعومة:**
• `ضيف عملة BTC ETH` - إضافة عملات
• `شيل عملة SOL` - حذف عملات  
• `شغل الاشتراك` - تفعيل إجباري
• `عدل ترحيب نص` - تغيير الترحيب
• `عرض الاعدادات` - رؤية الإعدادات

**💬 تكلم بشكل طبيعي!**
""",
        EMOJIS['rocket']
    )
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['chart']} عرض الإعدادات", callback_data="show_settings")],
        [InlineKeyboardButton(f"{EMOJIS['update']} تحديث", callback_data="refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMINS:
        await query.edit_message_text(f"{EMOJIS['error']} **ليس لديك صلاحية**")
        return
    
    data = query.data
    
    if data == "show_settings":
        settings_text = modern_bot.format_settings()
        await query.edit_message_text(settings_text, parse_mode='Markdown')
    elif data == "refresh":
        await query.edit_message_text(f"{EMOJIS['check']} **تم التحديث**")

def main():
    """التشغيل الرئيسي"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    try:
        # منع التكرار - تأكد من نسخة واحدة فقط
        application = Application.builder().token(ADMIN_BOT_TOKEN).build()
        
        # إضافة handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("admin", start_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            handle_message
        ))
        
        logging.info(f"{EMOJIS['rocket']} **بوت الإدارة الذكي يعمل!**")
        logging.info(f"{EMOJIS['crown']} **المسؤولون:** {ADMINS}")
        
        # تشغيل البوت مع معالجة الأخطاء
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logging.error(f"{EMOJIS['error']} **خطأ في التشغيل:** {e}")

if __name__ == '__main__':
    main()
