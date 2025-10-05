import logging
import asyncio
import aiohttp
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# إعدادات بوت الإدارة - ضع التوكن الذي حصلت عليه هنا
ADMIN_BOT_TOKEN = "8205170895:AAE9D0BAnGWE3_5FyEtY08FP8bivzcv8XRY"
MAIN_BOT_TOKEN = "8122538449:AAGE9NIO18L6OqF5DZlQxsIK6x7LdHDJwmA"

# ضع رقمك كمسؤول (اسألني كيف تعرف رقمك على Telegram)
ADMINS = [123456789]  # استبدل هذا برقمك

class SmartAIAdminBot:
    def __init__(self):
        self.bot_settings = self.load_settings()
        self.setup_commands()
    
    def setup_commands(self):
        self.available_commands = {
            "add_subscription": {
                "keywords": ["اشتراك اجباري", "إجباري", "اشتراك", "subscription"],
                "function": self.enable_subscription
            },
            "remove_subscription": {
                "keywords": ["إلغاء الاشتراك", "إلغاء إجباري", "إلغاء"],
                "function": self.disable_subscription
            },
            "add_donation": {
                "keywords": ["تبرع", "دعم", "donation", "تبرعات"],
                "function": self.add_donation_link
            },
            "add_trending_coin": {
                "keywords": ["ضيف عملة", "إضافة عملة", "عملة جديدة", "add coin"],
                "function": self.add_trending_coin
            },
            "remove_coin": {
                "keywords": ["شيل عملة", "احذف عملة", "حذف عملة", "remove coin"],
                "function": self.remove_trending_coin
            },
            "change_welcome": {
                "keywords": ["عدل ترحيب", "تغيير ترحيب", "رسالة ترحيب", "welcome"],
                "function": self.change_welcome_message
            },
            "broadcast": {
                "keywords": ["اذاعة", "بث", "رسالة جماعية", "broadcast"],
                "function": self.prepare_broadcast
            }
        }
    
    def load_settings(self):
        try:
            return {
                "welcome_message": "🌟 مرحباً بك في بوت الأسعار المتقدم!",
                "subscription_required": False,
                "subscription_channel": "@zforexms",
                "trending_coins": ["BTC", "ETH", "SOL", "TON", "XRP"],
                "donation_link": "",
                "broadcast_message": "",
                "custom_buttons": []
            }
        except:
            return self.load_settings()
    
    def save_settings(self, settings=None):
        if settings:
            self.bot_settings = settings
        print("✅ تم حفظ الإعدادات")
    
    async def analyze_command(self, user_message):
        message_lower = user_message.lower()
        
        for command, info in self.available_commands.items():
            for keyword in info['keywords']:
                if keyword in message_lower:
                    return {
                        "command": command,
                        "parameters": self.extract_parameters(user_message, command),
                        "response": f"تم التعرف على الأمر: {keyword}",
                        "action_required": True
                    }
        
        return {
            "command": "unknown",
            "response": "لم أفهم الأمر. جرب:\n• 'ضيف عملة BTC'\n• 'شغل الاشتراك الإجباري'\n• 'عدل ترحيب مرحباً'",
            "action_required": False
        }
    
    def extract_parameters(self, message, command):
        params = {}
        
        if command == "add_trending_coin":
            coins = re.findall(r'[A-Z]{2,5}', message.upper())
            params['coins'] = [coin for coin in coins if coin not in ['ADD', 'REMOVE', 'COIN']]
        
        elif command == "add_donation":
            links = re.findall(r'https?://[^\s]+', message)
            if links:
                params['donation_link'] = links[0]
        
        elif command == "change_welcome":
            welcome_text = message.replace('ترحيب', '').replace('welcome', '').strip()
            params['welcome_message'] = welcome_text
        
        elif command == "broadcast":
            broadcast_text = message.replace('اذاعة', '').replace('بث', '').strip()
            params['broadcast_text'] = broadcast_text
        
        return params
    
    async def execute_command(self, command, parameters):
        try:
            if command in self.available_commands:
                result = await self.available_commands[command]['function'](parameters)
                return result
            return "❌ الأمر غير معروف"
        except Exception as e:
            return f"❌ خطأ في التنفيذ: {str(e)}"
    
    async def enable_subscription(self, params):
        self.bot_settings["subscription_required"] = True
        self.save_settings()
        return "✅ تم تفعيل الاشتراك الإجباري بنجاح"
    
    async def disable_subscription(self, params):
        self.bot_settings["subscription_required"] = False
        self.save_settings()
        return "✅ تم إلغاء الاشتراك الإجباري بنجاح"
    
    async def add_donation_link(self, params):
        if 'donation_link' in params:
            self.bot_settings["donation_link"] = params['donation_link']
            self.save_settings()
            return f"✅ تم إضافة رابط التبرع: {params['donation_link']}"
        return "❌ لم يتم تقديم رابط التبرع"
    
    async def add_trending_coin(self, params):
        if 'coins' in params and params['coins']:
            new_coins = []
            for coin in params['coins']:
                if coin not in self.bot_settings["trending_coins"]:
                    self.bot_settings["trending_coins"].append(coin)
                    new_coins.append(coin)
            
            self.save_settings()
            if new_coins:
                return f"✅ تمت إضافة العملات: {', '.join(new_coins)}"
            else:
                return "ℹ️ العملات موجودة بالفعل"
        return "❌ لم يتم تحديد عملات للإضافة"
    
    async def remove_trending_coin(self, params):
        if 'coins' in params and params['coins']:
            removed_coins = []
            for coin in params['coins']:
                if coin in self.bot_settings["trending_coins"]:
                    self.bot_settings["trending_coins"].remove(coin)
                    removed_coins.append(coin)
            
            self.save_settings()
            if removed_coins:
                return f"✅ تم حذف العملات: {', '.join(removed_coins)}"
            else:
                return "❌ العملات غير موجودة في القائمة"
        return "❌ لم يتم تحديد عملات للحذف"
    
    async def change_welcome_message(self, params):
        if 'welcome_message' in params:
            self.bot_settings["welcome_message"] = params['welcome_message']
            self.save_settings()
            return "✅ تم تحديث رسالة الترحيب بنجاح"
        return "❌ لم يتم تقديم نص الترحيب"
    
    async def prepare_broadcast(self, params):
        if 'broadcast_text' in params:
            self.bot_settings["broadcast_message"] = params['broadcast_text']
            self.save_settings()
            return f"✅ تم حفظ رسالة البث"
        return "❌ لم يتم تقديم نص البث"

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول")
        return
    
    user_message = update.message.text
    
    if not context.bot_data.get('admin_bot'):
        context.bot_data['admin_bot'] = SmartAIAdminBot()
    
    admin_bot = context.bot_data['admin_bot']
    
    loading_msg = await update.message.reply_text("🤔 جاري تحليل طلبك...")
    
    ai_analysis = await admin_bot.analyze_command(user_message)
    
    if ai_analysis['action_required']:
        result = await admin_bot.execute_command(
            ai_analysis['command'], 
            ai_analysis['parameters']
        )
        response_message = f"{ai_analysis['response']}\n\n{result}"
    else:
        response_message = ai_analysis['response']
    
    await loading_msg.edit_text(response_message)

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول")
        return
    
    welcome_text = """
🤖 **بوت الإدارة الذكي**

يمكنك التحدث معي بشكل طبيعي:

🔹 **إدارة الاشتراك**
• "شغل الاشتراك الإجباري"
• "إلغاء الاشتراك الإجباري"

🔹 **إدارة العملات**
• "ضيف عملة BTC"
• "شيل عملة ETH"

🔹 **التخصيص**
• "عدل ترحيب مرحباً بك"
• "ضيف رابط تبرع https://..."

🔹 **البث**
• "اعمل اذاعة Hello everyone"

**تكلم معي naturally! 🎯**
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

def main():
    application = Application.builder().token(ADMIN_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", admin_start))
    application.add_handler(CommandHandler("admin", admin_start))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_admin_message
    ))
    
    print("🤖 بوت الإدارة الذكي يعمل الآن!")
    application.run_polling()

if __name__ == '__main__':

    main()
