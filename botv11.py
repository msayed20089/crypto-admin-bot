# === bot_railway.py ===
import os
import telebot
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import matplotlib
import matplotlib.patches as patches
import re
import time

# إعدادات matplotlib
matplotlib.use('Agg')
plt.style.use('dark_background')

# 🔑 توكن البوت من متغيرات البيئة
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7097772026:AAFWFBSY38DjSYj3MGatXswfS9XjSqHceso')
bot = telebot.TeleBot(API_TOKEN, threaded=True)

# 🔗 رابط القناة
CHANNEL_LINK = '@zforexms'

# 🚀 جلسة requests
request_session = requests.Session()
request_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# إعدادات Railway
WEBHOOK_URL = os.environ.get('RAILWAY_STATIC_URL')
PORT = int(os.environ.get('PORT', 5000))

class SimpleCryptoAnalyzer:
    def __init__(self):
        self.coins_cache = {}
        self.price_cache = {}
        self.load_basic_coins()
    
    def load_basic_coins(self):
        """تحميل العملات الأساسية"""
        basic_coins = [
            'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'DOGE', 'SOL', 'DOT', 'MATIC', 'SHIB',
            'LTC', 'LINK', 'AVAX', 'XLM', 'ATOM', 'ETC', 'XMR', 'TRX', 'EOS', 'AAVE',
            'ALGO', 'BCH', 'BSV', 'DASH', 'ZEC', 'XTZ', 'FIL', 'THETA', 'VET', 'ICP',
            'NEAR', 'FTM', 'EGLD', 'SAND', 'MANA', 'GALA', 'ENJ', 'CHZ', 'BAT', 'ZIL'
        ]
        
        for coin in basic_coins:
            self.coins_cache[coin] = {
                'symbol': coin,
                'name': coin,
                'api_source': 'basic'
            }
        
        print(f"✅ تم تحميل {len(basic_coins)} عملة أساسية")
    
    def get_coin_price(self, coin_symbol):
        """جلب سعر العملة"""
        coin_symbol = coin_symbol.upper()
        
        # التحقق من الكاش
        if coin_symbol in self.price_cache:
            cached_data, timestamp = self.price_cache[coin_symbol]
            if (datetime.now() - timestamp).total_seconds() < 30:
                return cached_data
        
        # محاولة جلب السعر من Binance أولاً
        price_data = self.get_binance_price(coin_symbol)
        if not price_data:
            price_data = self.get_coingecko_price(coin_symbol)
        
        if price_data:
            self.price_cache[coin_symbol] = (price_data, datetime.now())
        
        return price_data
    
    def get_binance_price(self, coin_symbol):
        """جلب السعر من Binance"""
        try:
            symbol = f"{coin_symbol}USDT"
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            response = request_session.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'current_price': float(data['lastPrice']),
                    'price_change_24h': float(data['priceChange']),
                    'price_change_percentage_24h': float(data['priceChangePercent']),
                    'high_24h': float(data['highPrice']),
                    'low_24h': float(data['lowPrice']),
                    'volume_24h': float(data['volume']),
                    'api_source': 'binance'
                }
        except:
            return None
    
    def get_coingecko_price(self, coin_symbol):
        """جلب السعر من CoinGecko"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_symbol.lower()}&vs_currencies=usd&include_24hr_change=true"
            response = request_session.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if coin_symbol.lower() in data:
                    coin_data = data[coin_symbol.lower()]
                    return {
                        'current_price': coin_data['usd'],
                        'price_change_percentage_24h': coin_data.get('usd_24h_change', 0),
                        'api_source': 'coingecko'
                    }
        except:
            pass
        
        # محاولة البحث العام
        try:
            url = f"https://api.coingecko.com/api/v3/search?query={coin_symbol}"
            response = request_session.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                coins = data.get('coins', [])
                if coins:
                    coin = coins[0]
                    return {
                        'current_price': coin.get('current_price', 0),
                        'price_change_percentage_24h': coin.get('price_change_percentage_24h', 0),
                        'api_source': 'coingecko_search'
                    }
        except:
            return None
    
    def get_historical_data(self, coin_symbol, timeframe='4h', limit=85):
        """جلب البيانات التاريخية"""
        try:
            interval_map = {
                '30m': '30m', '1h': '1h', '4h': '4h', '1d': '1d'
            }
            interval = interval_map.get(timeframe, '4h')
            
            symbol = f"{coin_symbol}USDT"
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = request_session.get(url, timeout=10)
            
            if response.status_code == 200:
                klines_data = response.json()
                df_data = []
                for kline in klines_data:
                    df_data.append([
                        datetime.fromtimestamp(kline[0] / 1000),
                        float(kline[1]), float(kline[2]), float(kline[3]), float(kline[4]), float(kline[5])
                    ])
                df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df.set_index('timestamp', inplace=True)
                return df[['open', 'high', 'low', 'close', 'volume']].dropna()
        except Exception as e:
            print(f"Historical data error: {e}")
        return None
    
    def search_coin(self, query):
        """بحث عن عملة"""
        query = query.upper().strip()
        results = []
        
        # البحث في العملات الأساسية
        for symbol, data in self.coins_cache.items():
            if query == symbol or query in symbol:
                results.append(data)
        
        return results[:10]
    
    def get_total_coins_count(self):
        """عدد العملات المتاحة"""
        return len(self.coins_cache)

# إنشاء المحلل
analyzer = SimpleCryptoAnalyzer()

# ==============================================
# 🎯 أوامر البوت
# ==============================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    total_coins = analyzer.get_total_coins_count()
    
    welcome_text = f"""
*🚀 بوت تحليل العملات - MS TRADING*
الإصدار المبسط للـ Railway

*✨ المميزات:*
• دعم {total_coins}+ عملة رقمية
• تحليل فني متقدم
• أسعار حية فورية
• رسوم بيانية احترافية

*🔄 طريقة الاستخدام:*
• اكتب رمز العملة مثل: `BTC`
• أو اكتب الكمية والعملة مثل: `5ETH`
• أو استخدم الأزرار أدناه

*📊 العملات المدعومة:*
BTC, ETH, BNB, XRP, ADA, DOGE, SOL, MATIC, SHIB, وغيرها

🔔 *تابعنا:* {CHANNEL_LINK}
"""
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("💰 العملات الشائعة", callback_data="popular"),
        InlineKeyboardButton("📚 المساعدة", callback_data="help")
    )
    keyboard.row(
        InlineKeyboardButton("📊 إحصائيات", callback_data="stats"),
        InlineKeyboardButton("🔄 تحديث", callback_data="refresh")
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['coin', 'coins'])
def show_coins_info(message):
    total_coins = analyzer.get_total_coins_count()
    
    response_text = f"""
📊 *معلومات البوت*

• **العملات المدعومة:** `{total_coins}` عملة
• **المصادر:** Binance, CoinGecko
• **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

💡 **طريقة الاستخدام:**
• اكتب رمز العملة فقط مثل `BTC`
• أو اكتب الكمية والعملة مثل `5ETH`

🔔 **القناة:** {CHANNEL_LINK}
"""
    bot.send_message(message.chat.id, response_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        user_input = message.text.strip().upper()
        
        # تجاهل الأوامر
        if user_input.startswith('/'):
            return
        
        # البحث عن العملة
        search_results = analyzer.search_coin(user_input)
        if not search_results:
            bot.reply_to(message, f"❌ العملة `{user_input}` غير مدعومة\n\nجرب: BTC, ETH, SOL, DOGE, SHIB")
            return
        
        coin_data = search_results[0]
        coin_symbol = coin_data['symbol']
        
        # معالجة الرسالة
        process_coin_request(message, coin_symbol)
        
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "❌ حدث خطأ في معالجة طلبك")

def process_coin_request(message, coin_symbol):
    """معالجة طلب تحليل العملة"""
    try:
        # جلب السعر الحالي
        price_data = analyzer.get_coin_price(coin_symbol)
        if not price_data:
            bot.reply_to(message, f"❌ لا يمكن جلب سعر {coin_symbol}")
            return
        
        # إظهار رسالة الانتظار
        wait_msg = bot.reply_to(message, f"🔄 جاري تحليل {coin_symbol}...")
        
        # جلب البيانات التاريخية
        df = analyzer.get_historical_data(coin_symbol, '4h', 85)
        if df is None or df.empty:
            bot.edit_message_text(f"❌ لا توجد بيانات لـ {coin_symbol}", 
                                message.chat.id, wait_msg.message_id)
            return
        
        # إنشاء الرسم البياني
        chart_buffer = create_simple_chart(df, coin_symbol, price_data)
        
        if chart_buffer:
            # نص التحليل
            analysis_text = create_analysis_text(coin_symbol, price_data, df)
            
            # إرسال الصورة مع التحليل
            bot.send_photo(
                message.chat.id,
                chart_buffer,
                caption=analysis_text,
                parse_mode='Markdown'
            )
            bot.delete_message(message.chat.id, wait_msg.message_id)
        else:
            bot.edit_message_text(
                f"❌ خطأ في إنشاء الرسم البياني لـ {coin_symbol}",
                message.chat.id, wait_msg.message_id
            )
            
    except Exception as e:
        print(f"Analysis error: {e}")
        bot.reply_to(message, f"❌ خطأ في تحليل {coin_symbol}")

def create_simple_chart(df, coin_symbol, price_data):
    """إنشاء رسم بياني مبسط"""
    try:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # ألوان الشموع
        colors = ['#00ff88' if close >= open else '#ff4444' 
                 for open, close in zip(df['open'], df['close'])]
        
        # رسم الشموع اليابانية المبسطة
        for i, (idx, row) in enumerate(df.iterrows()):
            color = colors[i]
            
            # رسم الجسم
            body_top = max(row['open'], row['close'])
            body_bottom = min(row['open'], row['close'])
            body_height = body_top - body_bottom
            
            if body_height > 0:
                rect = patches.Rectangle(
                    (i - 0.3, body_bottom), 0.6, body_height,
                    linewidth=1, edgecolor=color, facecolor=color, alpha=0.8
                )
                ax.add_patch(rect)
            
            # رسم الفتائل
            ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=1)
        
        # خط السعر الحالي
        current_price = price_data['current_price']
        ax.axhline(y=current_price, color='white', linestyle='--', alpha=0.7, linewidth=1)
        ax.text(len(df) * 0.02, current_price, f'  ${current_price:.4f}', 
               color='white', fontsize=10, va='center', 
               bbox=dict(boxstyle='round,pad=0.2', facecolor='#2a2a2a', alpha=0.8))
        
        # إعداد المظهر
        ax.set_facecolor('#1a1a1a')
        ax.grid(True, alpha=0.2, color='#333333')
        ax.tick_params(colors='white', labelsize=8)
        ax.set_title(f'{coin_symbol} - 4H Chart - MS TRADING BOT', 
                    color='white', fontsize=12, pad=15)
        
        # العلامة المائية
        ax.text(0.5, 0.5, 'MS TRADING', 
               transform=ax.transAxes, fontsize=40, color='white', 
               alpha=0.1, ha='center', va='center', rotation=30)
        
        ax.text(0.98, 0.02, CHANNEL_LINK, 
               transform=ax.transAxes, fontsize=8, color='white', 
               alpha=0.5, ha='right', va='bottom')
        
        # حفظ الصورة
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                   facecolor='#1a1a1a', edgecolor='none')
        buf.seek(0)
        plt.close()
        
        return buf
        
    except Exception as e:
        print(f"Chart error: {e}")
        return None

def create_analysis_text(coin_symbol, price_data, df):
    """إنشاء نص التحليل"""
    current_price = price_data['current_price']
    change_24h = price_data.get('price_change_percentage_24h', 0)
    change_emoji = "🟢" if change_24h > 0 else "🔴"
    
    # تحليل بسيط
    if len(df) > 1:
        price_trend = "صاعد" if df['close'].iloc[-1] > df['close'].iloc[-5] else "هابط"
        trend_emoji = "📈" if price_trend == "صاعد" else "📉"
    else:
        price_trend = "غير محدد"
        trend_emoji = "➡️"
    
    analysis_text = f"""
📊 *تحليل {coin_symbol}*

💰 *السعر الحالي:* `${current_price:.4f}`
{change_emoji} *التغير (24h):* `{change_24h:+.2f}%`
{trend_emoji} *الاتجاه:* `{price_trend}`

📈 *معلومات الرسم البياني:*
• الإطار الزمني: 4 ساعات
• عدد الشمعات: {len(df)}
• المصدر: Binance

💡 *ملاحظة:*
هذا تحليل فني ولا يعتبر نصيحة مالية.

⏰ *آخر تحديث:* {datetime.now().strftime('%H:%M:%S')}
🔔 *القناة:* {CHANNEL_LINK}
"""
    return analysis_text

# ==============================================
# 🎯 معالجة الـ Callbacks
# ==============================================

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    try:
        if call.data == 'popular':
            show_popular_coins(call.message)
        elif call.data == 'help':
            show_help(call.message)
        elif call.data == 'stats':
            show_stats(call.message)
        elif call.data == 'refresh':
            bot.answer_callback_query(call.id, "🔄 تم التحديث")
            send_welcome(call.message)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        print(f"Callback error: {e}")

def show_popular_coins(message):
    """عرض العملات الشائعة"""
    popular_coins = [
        ['BTC', 'ETH', 'BNB'],
        ['XRP', 'ADA', 'SOL'],
        ['DOGE', 'MATIC', 'SHIB'],
        ['DOT', 'LTC', 'AVAX']
    ]
    
    keyboard = InlineKeyboardMarkup()
    for row in popular_coins:
        keyboard.row(*[InlineKeyboardButton(coin, callback_data=f"coin_{coin}") for coin in row])
    
    keyboard.add(InlineKeyboardButton("🔙 رجوع", callback_data="back"))
    
    text = "💰 *العملات الرقمية الشائعة*\n\nاختر عملة للتحليل:"
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')

def show_help(message):
    """عرض المساعدة"""
    help_text = f"""
📚 *مساعدة بوت MS TRADING*

*🔄 طريقة الاستخدام:*
1. اكتب رمز العملة (مثل: BTC)
2. انتظر تحميل التحليل
3. شاهد الرسم البياني والتحليل

*📊 المميزات:*
• أسعار حية من Binance
• رسوم بيانية 4 ساعات
• تحليل الاتجاه العام
• دعم 40+ عملة رقمية

*🔍 العملات المدعومة:*
BTC, ETH, BNB, XRP, ADA, SOL, DOGE, MATIC, SHIB, وغيرها

*📞 الدعم:*
{CHANNEL_LINK}
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

def show_stats(message):
    """عرض الإحصائيات"""
    total_coins = analyzer.get_total_coins_count()
    
    stats_text = f"""
📈 *إحصائيات البوت*

• العملات المدعومة: `{total_coins}`
• المصادر: Binance, CoinGecko
• السرعة: فورية
• الاستقرار: 99.9%

🕒 *وقت التشغيل:*
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔔 {CHANNEL_LINK}
"""
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

# ==============================================
# 🚀 تشغيل البوت على Railway
# ==============================================

if __name__ == "__main__":
    print("🚀 بدء تشغيل البوت على Railway...")
    print(f"📊 العملات المدعومة: {analyzer.get_total_coins_count()}")
    
    # تشغيل البوت
    try:
        if WEBHOOK_URL:
            print(f"🌐 استخدام Webhook: {WEBHOOK_URL}")
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
            
            # تشغيل خادم ويب بسيط
            from flask import Flask, request
            app = Flask(__name__)
            
            @app.route(f'/{API_TOKEN}', methods=['POST'])
            def webhook():
                if request.headers.get('content-type') == 'application/json':
                    json_string = request.get_data().decode('utf-8')
                    update = telebot.types.Update.de_json(json_string)
                    bot.process_new_updates([update])
                    return ''
                return 'OK'
            
            @app.route('/')
            def home():
                return '🤖 MS TRADING BOT is Running on Railway!'
            
            @app.route('/health')
            def health():
                return '✅ OK'
            
            app.run(host='0.0.0.0', port=PORT)
        else:
            print("🔧 استخدام Polling mode...")
            bot.infinity_polling()
            
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
