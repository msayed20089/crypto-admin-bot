# === botv11_railway.py ===
import os
import telebot
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import io
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import matplotlib
import matplotlib.patches as patches
from scipy.signal import argrelextrema
import re
import concurrent.futures
import time
import json
import random

# استخدام backend غير تفاعلي لـ matplotlib
matplotlib.use('Agg')
plt.style.use('dark_background')

# 🔑 توكن البوت من متغيرات البيئة
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7097772026:AAFWFBSY38DjSYj3MGatXswfS9XjSqHceso')
bot = telebot.TeleBot(API_TOKEN, threaded=True)

# 🔗 رابط قناتك
CHANNEL_LINK = '@zforexms'

# 🚀 تحسين الأداء
request_session = requests.Session()
request_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

# إعدادات Railway
WEBHOOK_URL = os.environ.get('RAILWAY_STATIC_URL')
PORT = int(os.environ.get('PORT', 5000))

class SMCICTAnalyzer:
    def __init__(self):
        self.fvg_color = 'yellow'
        self.ob_color = 'magenta'
        self.support_color = 'green'
        self.resistance_color = 'red'
        self.liquidity_color = 'cyan'
        
    def detect_fvg(self, df, lookback=10):
        """كشف Fair Value Gaps"""
        fvg_points = []
        for i in range(lookback, len(df)-1):
            if df['low'].iloc[i] > df['high'].iloc[i+1]:
                fvg_points.append({
                    'type': 'FVG', 'start': i, 'end': i+1,
                    'price_top': df['low'].iloc[i], 'price_bottom': df['high'].iloc[i+1],
                    'color': 'yellow', 'label': 'FVG'
                })
            if df['high'].iloc[i] < df['low'].iloc[i+1]:
                fvg_points.append({
                    'type': 'FVG', 'start': i, 'end': i+1,
                    'price_top': df['low'].iloc[i+1], 'price_bottom': df['high'].iloc[i],
                    'color': 'yellow', 'label': 'FVG'
                })
        return fvg_points[-3:]

    def detect_order_blocks(self, df, window=10):
        """كشف Order Blocks"""
        ob_blocks = []
        for i in range(window, len(df)-window):
            if (df['close'].iloc[i] > df['open'].iloc[i] and 
                df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i] < df['low'].iloc[i+1]):
                ob_blocks.append({
                    'type': 'OB', 'index': i, 'high': df['high'].iloc[i], 'low': df['low'].iloc[i],
                    'color': 'magenta', 'label': 'OB'
                })
            if (df['close'].iloc[i] < df['open'].iloc[i] and 
                df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i] > df['high'].iloc[i+1]):
                ob_blocks.append({
                    'type': 'OB', 'index': i, 'high': df['high'].iloc[i], 'low': df['low'].iloc[i],
                    'color': 'magenta', 'label': 'OB'
                })
        return ob_blocks[-4:]

    def detect_liquidity_zones(self, df, window=15):
        """كشف مناطق السيولة"""
        liquidity_zones = []
        high_idx = argrelextrema(df['high'].values, np.greater, order=window)[0]
        for idx in high_idx[-3:]:
            liquidity_zones.append({
                'type': 'LIQUIDITY', 'index': idx, 'price': df['high'].iloc[idx],
                'color': 'cyan', 'label': 'LIQUIDITY'
            })
        low_idx = argrelextrema(df['low'].values, np.less, order=window)[0]
        for idx in low_idx[-3:]:
            liquidity_zones.append({
                'type': 'LIQUIDITY', 'index': idx, 'price': df['low'].iloc[idx],
                'color': 'cyan', 'label': 'LIQUIDITY'
            })
        return liquidity_zones

    def detect_support_resistance(self, df, window=15):
        """كشف الدعم والمقاومة"""
        support_levels = []
        resistance_levels = []
        high_idx = argrelextrema(df['high'].values, np.greater, order=window)[0]
        for idx in high_idx[-4:]:
            resistance_levels.append({
                'type': 'RESISTANCE', 'price': df['high'].iloc[idx],
                'color': 'red', 'label': 'RESISTANCE'
            })
        low_idx = argrelextrema(df['low'].values, np.less, order=window)[0]
        for idx in low_idx[-4:]:
            support_levels.append({
                'type': 'SUPPORT', 'price': df['low'].iloc[idx],
                'color': 'green', 'label': 'SUPPORT'
            })
        return {'support': support_levels, 'resistance': resistance_levels}

    def predict_movement_with_targets(self, df, signals, sr_levels):
        """توقع الحركة مع الأهداف"""
        if len(df) < 10:
            return {"direction": "NEUTRAL", "targets": [], "explanation": "لا توجد بيانات كافية"}
        
        current_price = df['close'].iloc[-1]
        supports = [s['price'] for s in sr_levels['support'] if s['price'] < current_price]
        resistances = [r['price'] for r in sr_levels['resistance'] if r['price'] > current_price]
        supports.sort(reverse=True)
        resistances.sort()
        
        targets = []
        price_trend = "UP" if current_price > df['close'].iloc[-5] else "DOWN"
        
        if price_trend == "UP" and resistances:
            next_resistance = resistances[0]
            targets.append({'type': 'RESISTANCE_TARGET', 'price': next_resistance, 'direction': 'UP'})
            explanation = f"متوقع الصعود نحو {next_resistance:.4f}"
            if len(resistances) > 1:
                targets.append({'type': 'SECONDARY_RESISTANCE', 'price': resistances[1], 'direction': 'UP'})
                explanation = f"متوقع الصعود نحو {next_resistance:.4f} ثم {resistances[1]:.4f}"
        elif price_trend == "DOWN" and supports:
            next_support = supports[0]
            targets.append({'type': 'SUPPORT_TARGET', 'price': next_support, 'direction': 'DOWN'})
            explanation = f"متوقع الهبوط نحو {next_support:.4f}"
            if len(supports) > 1:
                targets.append({'type': 'SECONDARY_SUPPORT', 'price': supports[1], 'direction': 'DOWN'})
                explanation = f"متوقع الهبوط نحو {next_support:.4f} ثم {supports[1]:.4f}"
        else:
            explanation = "السوق في حالة اتزان"
        
        return {
            "direction": "BULLISH" if price_trend == "UP" else "BEARISH",
            "targets": targets,
            "explanation": explanation
        }

class MegaCoinDatabase:
    def __init__(self):
        self.coins_data = {}
        self.price_cache = {}
        self.cache_timeout = 30
        self.total_coins_count = 0
        # تحميل قاعدة البيانات بشكل مخفف للـ Railway
        self.load_lightweight_database()
        
    def load_lightweight_database(self):
        """تحميل قاعدة بيانات مخففة للـ Railway"""
        print("🔄 جاري تحميل قاعدة بيانات مخففة...")
        
        sources = [
            self.load_historical_coins,
            self.load_binance_all,
            self.load_coingecko_light
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(source) for source in sources]
            concurrent.futures.wait(futures, timeout=60)
        
        print(f"✅ تم تحميل {self.total_coins_count:,} عملة!")
    
    def load_coingecko_light(self):
        """تحميل مخفف من CoinGecko"""
        try:
            print("📥 جاري تحميل من CoinGecko (مخفف)...")
            categories = ['cryptocurrency', 'decentralized-finance-defi', 'meme-token']
            
            all_coins = []
            
            for category in categories:
                url = "https://api.coingecko.com/api/v3/coins/markets"
                params = {
                    'vs_currency': 'usd',
                    'category': category,
                    'order': 'market_cap_desc',
                    'per_page': 100,
                    'page': 1,
                    'sparkline': 'false'
                }
                try:
                    response = request_session.get(url, params=params, timeout=20)
                    if response.status_code == 200:
                        coins = response.json()
                        if coins:
                            all_coins.extend(coins)
                            print(f"✅ CoinGecko {category}: {len(coins)} عملة")
                    time.sleep(1.2)
                except Exception as e:
                    print(f"⚠️ CoinGecko {category} error: {e}")
                    continue
            
            count = 0
            for coin in all_coins:
                symbol = coin['symbol'].upper()
                if symbol and symbol not in self.coins_data:
                    self.coins_data[symbol] = {
                        'id': coin['id'],
                        'name': coin['name'],
                        'symbol': symbol,
                        'api_source': 'coingecko',
                        'market_cap_rank': coin.get('market_cap_rank', 99999),
                        'current_price': coin.get('current_price', 0),
                        'market_cap': coin.get('market_cap', 0)
                    }
                    count += 1
            
            self.total_coins_count += count
            print(f"✅ CoinGecko: {count:,} عملة جديدة")
            
        except Exception as e:
            print(f"❌ CoinGecko error: {e}")
    
    def load_binance_all(self):
        """تحميل جميع أزواج Binance"""
        try:
            print("📥 جاري تحميل من Binance...")
            url = "https://api.binance.com/api/v3/exchangeInfo"
            response = request_session.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                symbols = data['symbols']
                count = 0
                for symbol_info in symbols:
                    if symbol_info['status'] == 'TRADING':
                        base_asset = symbol_info['baseAsset']
                        if base_asset not in self.coins_data:
                            self.coins_data[base_asset] = {
                                'id': base_asset.lower(),
                                'name': base_asset,
                                'symbol': base_asset,
                                'api_source': 'binance',
                                'market_cap_rank': 99999
                            }
                            count += 1
                self.total_coins_count += count
                print(f"✅ Binance: {count:,} عملة جديدة")
        except Exception as e:
            print(f"❌ Binance error: {e}")
    
    def load_historical_coins(self):
        """تحميل العملات التاريخية"""
        try:
            print("📥 جاري تحميل العملات التاريخية...")
            historical_coins = [
                'BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'ADA', 'DOT', 'LINK', 'XLM', 'XMR',
                'ETC', 'ZEC', 'DASH', 'DOGE', 'BSV', 'EOS', 'TRX', 'XTZ', 'ATOM', 'ALGO',
                'NEO', 'ONT', 'VET', 'ICX', 'QTUM', 'ZIL', 'BAT', 'OMG', 'ZRX', 'REP',
                'KNC', 'MANA', 'ENJ', 'SNT', 'CVC', 'LOOM', 'POLY', 'POWR', 'STORJ', 'KIN',
                'SOL', 'BNB', 'AVAX', 'MATIC', 'FTM', 'ONE', 'NEAR', 'FLOW', 'ROSE', 'CELO'
            ]
            
            count = 0
            for symbol in historical_coins:
                if symbol not in self.coins_data:
                    self.coins_data[symbol] = {
                        'id': symbol.lower(),
                        'name': symbol,
                        'symbol': symbol,
                        'api_source': 'historical',
                        'market_cap_rank': 99999
                    }
                    count += 1
            
            self.total_coins_count += count
            print(f"✅ العملات التاريخية: {count:,} عملة جديدة")
            
        except Exception as e:
            print(f"❌ Historical coins error: {e}")

    # باقي الدوال تبقى كما هي مع تعديلات طفيفة للأداء
    def get_coin_price(self, coin_symbol):
        """جلب سعر العملة من أفضل مصدر"""
        coin_symbol = coin_symbol.upper()
        
        # التحقق من الكاش أولاً
        if coin_symbol in self.price_cache:
            cached_data, timestamp = self.price_cache[coin_symbol]
            if (datetime.now() - timestamp).total_seconds() < self.cache_timeout:
                return cached_data
        
        # محاولة جلب السعر من مصادر متعددة
        price_sources = [
            self.get_binance_price,
            self.get_coingecko_price,
            self.get_dex_screener_price
        ]
        
        for price_func in price_sources:
            try:
                price_data = price_func(coin_symbol)
                if price_data and price_data.get('current_price', 0) > 0:
                    self.price_cache[coin_symbol] = (price_data, datetime.now())
                    return price_data
            except:
                continue
        
        return None

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
            coin_data = self.coins_data.get(coin_symbol)
            if coin_data and 'coingecko' in coin_data.get('api_source', ''):
                coin_id = coin_data.get('id')
                if coin_id:
                    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                    response = request_session.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        market_data = data.get('market_data', {})
                        return {
                            'current_price': market_data.get('current_price', {}).get('usd', 0),
                            'price_change_24h': market_data.get('price_change_24h', {}).get('usd', 0),
                            'price_change_percentage_24h': market_data.get('price_change_percentage_24h', {}).get('usd', 0),
                            'high_24h': market_data.get('high_24h', {}).get('usd', 0),
                            'low_24h': market_data.get('low_24h', {}).get('usd', 0),
                            'volume_24h': market_data.get('total_volume', {}).get('usd', 0),
                            'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                            'api_source': 'coingecko'
                        }
        except:
            return None

    def get_dex_screener_price(self, coin_symbol):
        """جلب السعر من DexScreener"""
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={coin_symbol}"
            response = request_session.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])
                if pairs:
                    pair = pairs[0]
                    return {
                        'current_price': float(pair.get('priceUsd', 0)),
                        'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                        'price_change_percentage_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                        'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                        'liquidity': float(pair.get('liquidity', {}).get('usd', 0)),
                        'api_source': 'dex_screener'
                    }
        except:
            return None

    def get_total_coins_count(self):
        """إرجاع عدد العملات الإجمالي"""
        return self.total_coins_count

    def search_coin(self, query):
        """بحث عن عملة"""
        query = query.upper().strip()
        results = []
        
        # البحث المباشر أولاً
        if query in self.coins_data:
            results.append(self.coins_data[query])
        
        # البحث في الرموز (partial match)
        for symbol, data in self.coins_data.items():
            if query in symbol:
                results.append(data)
        
        # البحث في الأسماء إذا لم نجد نتائج كافية
        if len(results) < 10:
            for symbol, data in self.coins_data.items():
                if query in data.get('name', '').upper():
                    results.append(data)
        
        return results[:20]  # إرجاع أول 20 نتيجة فقط

class ProfessionalCryptoAnalyzer:
    def __init__(self):
        self.coin_database = MegaCoinDatabase()
        self.smc_analyzer = SMCICTAnalyzer()
        
    def get_live_market_data(self, coin_symbol):
        """جلب بيانات السوق الحية"""
        return self.coin_database.get_coin_price(coin_symbol)
    
    def calculate_coin_value(self, amount, coin_symbol):
        """حساب قيمة العملة"""
        try:
            price_data = self.get_live_market_data(coin_symbol)
            if price_data and price_data.get('current_price'):
                total_value = amount * price_data['current_price']
                return total_value, price_data['current_price']
        except Exception as e:
            print(f"Error calculating value: {e}")
        return None, None

    def get_quick_price(self, coin_symbol):
        """طريقة سريعة للحصول على السعر"""
        price_data = self.get_live_market_data(coin_symbol)
        return price_data['current_price'] if price_data else None

    def get_historical_data_with_timeframe(self, coin_symbol, timeframe='1h', days=30):
        """جلب بيانات تاريخية"""
        timeframe_map = {
            '30m': ('30m', 48), '1h': ('1h', 24), 
            '4h': ('4h', 6), '1d': ('1d', 1)
        }
        binance_tf, hours_per_day = timeframe_map.get(timeframe, ('1h', 24))
        limit = min(days * hours_per_day, 85)
        return self.get_binance_historical_tf(coin_symbol, binance_tf, limit)

    def get_binance_historical_tf(self, coin_symbol, interval='1h', limit=85):
        """جلب بيانات تاريخية من Binance"""
        try:
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
            print(f"Binance historical error: {e}")
        return None

    def create_smc_ict_chart(self, df, coin_name, market_data, timeframe='1h', amount=None):
        """إنشاء مخطط SMC و ICT"""
        try:
            if df is None or df.empty:
                return None, "لا توجد بيانات متاحة"
                
            df = df.iloc[-85:]
            fvg_signals = self.smc_analyzer.detect_fvg(df)
            ob_signals = self.smc_analyzer.detect_order_blocks(df)
            liquidity_signals = self.smc_analyzer.detect_liquidity_zones(df)
            sr_levels = self.smc_analyzer.detect_support_resistance(df)
            all_signals = fvg_signals + ob_signals + liquidity_signals
            prediction_data = self.smc_analyzer.predict_movement_with_targets(df, all_signals, sr_levels)

            # إنشاء المخطط
            fig, ax = plt.subplots(figsize=(16, 10))
            ax.set_position([0.08, 0.10, 0.67, 0.85])
            
            # رسم الشموع
            for i, (idx, row) in enumerate(df.iterrows()):
                color = '#00ff88' if row['close'] >= row['open'] else '#ff4444'
                body_top = max(row['open'], row['close'])
                body_bottom = min(row['open'], row['close'])
                body_height = body_top - body_bottom
                if body_height > 0:
                    rect = patches.Rectangle((i - 0.4, body_bottom), 0.8, body_height,
                        linewidth=1, edgecolor=color, facecolor=color, alpha=0.9)
                    ax.add_patch(rect)
                ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=1.5)
            
            # إضافة المستطيلات
            self.add_smc_ict_rectangles(ax, df, all_signals, sr_levels)
            self.add_prediction_arrows(ax, df, prediction_data)
            
            # إضافة خط السعر الحالي
            current_price = market_data['current_price']
            ax.axhline(y=current_price, color='white', linestyle='--', linewidth=1, alpha=0.7)
            ax.text(len(df) * 0.02, current_price, f'  ${current_price:.4f}', 
                   color='white', fontsize=10, va='center', ha='left',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='#2a2a2a', alpha=0.8))
            
            # العلامات المائية
            ax.text(0.5, 0.5, 'MS TRADING BOT', 
                   transform=ax.transAxes, fontsize=40, color='white', 
                   alpha=0.07, ha='center', va='center', rotation=30, fontweight='bold')
            
            ax.text(0.02, 0.98, 'MS TRADING BOT', 
                   transform=ax.transAxes, fontsize=12, color='white', 
                   alpha=0.3, ha='left', va='top')
            
            ax.text(0.98, 0.98, CHANNEL_LINK, 
                   transform=ax.transAxes, fontsize=10, color='white', 
                   alpha=0.4, ha='right', va='top')
            
            # إعداد المظهر
            ax.grid(True, alpha=0.2, color='#333333')
            ax.set_facecolor('#1a1a1a')
            ax.tick_params(axis='y', colors='#CCCCCC', labelsize=10)
            ax.yaxis.set_label_position("right")
            ax.yaxis.tick_right()
            ax.tick_params(axis='x', colors='#CCCCCC', labelsize=9)
            ax.set_title(f'{coin_name} - {timeframe.upper()} - SMC/ICT ANALYSIS', 
                        color='white', fontsize=14, pad=20, fontweight='bold')
            
            # معلومات إضافية
            info_text = f"Current: {current_price:.4f} | TF: {timeframe.upper()}\nCandles: 85"
            if amount:
                total_value, price = self.calculate_coin_value(amount, coin_name)
                if total_value:
                    info_text += f"\n{amount} {coin_name} = ${total_value:.2f}"

            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, color='white', fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='#2a2a2a', alpha=0.9),
                   verticalalignment='top')

            # حفظ الصورة
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', pad_inches=0.1,
                       facecolor='#1a1a1a', edgecolor='none')
            buf.seek(0)
            plt.close('all')
            
            analysis_text = self.generate_smc_ict_analysis(market_data, all_signals, sr_levels, prediction_data, amount)
            return buf, analysis_text

        except Exception as e:
            print(f"SMC/ICT chart creation error: {e}")
            return None, f"خطأ في إنشاء الرسم البياني: {str(e)}"

    def add_smc_ict_rectangles(self, ax, df, signals, sr_levels):
        """إضافة مستطيلات SMC و ICT"""
        for signal in signals:
            if signal['type'] == 'FVG':
                rect = patches.Rectangle((signal['start'] - 0.5, signal['price_bottom']), 
                    1.0, signal['price_top'] - signal['price_bottom'],
                    linewidth=2, edgecolor=signal['color'], facecolor=signal['color'], alpha=0.4)
                ax.add_patch(rect)
                ax.text(signal['start'], (signal['price_top'] + signal['price_bottom']) / 2,
                       signal['label'], ha='center', va='center', color='black', fontsize=9, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor=signal['color'], alpha=0.8))

        right_start = len(df) * 0.75
        for support in sr_levels['support'][-3:]:
            rect = patches.Rectangle((right_start, support['price'] - 0.001), 
                len(df) * 0.23, 0.002, linewidth=2, edgecolor=support['color'], 
                facecolor=support['color'], alpha=0.5)
            ax.add_patch(rect)
            ax.text(right_start + (len(df) * 0.23)/2, support['price'], f" {support['label']} ", 
                   ha='center', va='center', color='black', fontsize=8, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor=support['color'], alpha=0.8))

    def add_prediction_arrows(self, ax, df, prediction_data):
        """إضافة أسهم التنبؤ"""
        current_price = df['close'].iloc[-1]
        arrow_start_x = len(df) * 0.75
        arrow_end_x = len(df) * 0.95
        targets = prediction_data['targets']
        
        if prediction_data['direction'] == "BULLISH" and targets:
            for i, target in enumerate(targets[:2]):
                ax.annotate('', xy=(arrow_end_x, target['price']), 
                           xytext=(arrow_start_x, current_price),
                           arrowprops=dict(arrowstyle='->', color='#00ff88', lw=3, alpha=0.8))
                ax.text(arrow_end_x, target['price'], f"Target {i+1}\n{target['price']:.4f}",
                       ha='left', va='center', color='#00ff88', fontsize=9, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='#1a1a1a', alpha=0.9))
        
        elif prediction_data['direction'] == "BEARISH" and targets:
            for i, target in enumerate(targets[:2]):
                ax.annotate('', xy=(arrow_end_x, target['price']), 
                           xytext=(arrow_start_x, current_price),
                           arrowprops=dict(arrowstyle='->', color='#ff4444', lw=3, alpha=0.8))
                ax.text(arrow_end_x, target['price'], f"Target {i+1}\n{target['price']:.4f}",
                       ha='left', va='center', color='#ff4444', fontsize=9, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='#1a1a1a', alpha=0.9))

    def generate_smc_ict_analysis(self, market_data, signals, sr_levels, prediction_data, amount=None):
        """توليد نص التحليل"""
        analysis = "📊 *تحليل SMC و ICT*\n\n🎯 *معلومات السوق:*\n"
        analysis += f"• السعر الحالي: `${market_data['current_price']:.4f}`\n"
        change_emoji = "🟢" if market_data.get('price_change_percentage_24h', 0) > 0 else "🔴"
        analysis += f"• التغير (24h): {change_emoji} `{market_data.get('price_change_percentage_24h', 0):+.2f}%`\n"
        
        if amount:
            total_value, price = self.calculate_coin_value(amount, market_data.get('symbol', 'UNKNOWN'))
            if total_value:
                analysis += f"• القيمة: `{amount} {market_data.get('symbol', 'UNKNOWN')} = ${total_value:.2f}`\n"
        
        analysis += f"• الاتجاه: `{prediction_data['direction']}`\n\n📈 *مستويات الدعم والمقاومة:*\n"
        for support in sr_levels['support'][-3:]:
            analysis += f"• الدعم: `${support['price']:.4f}`\n"
        for resistance in sr_levels['resistance'][-3:]:
            analysis += f"• المقاومة: `${resistance['price']:.4f}`\n"
        
        analysis += f"\n💡 *التوقعات:*\n{prediction_data['explanation']}\n"
        
        if prediction_data['targets']:
            analysis += "\n🎯 *الأهداف المتوقعة:*\n"
            for i, target in enumerate(prediction_data['targets'][:2]):
                analysis += f"• الهدف {i+1}: `${target['price']:.4f}`\n"
        
        analysis += f"\n⏰ آخر تحديث: {datetime.now().strftime('%H:%M:%S')}\n🔔 القناة: {CHANNEL_LINK}"
        return analysis

# إنشاء المحلل
analyzer = ProfessionalCryptoAnalyzer()

# ==============================================
# 🚀 إعدادات Railway
# ==============================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    total_coins = analyzer.coin_database.get_total_coins_count()
    
    welcome_text = f"""
*🚀 بوت تحليل العملات - SMC/ICT*
الإصدار Railway - قاعدة بيانات مخففة

*✨ المميزات:*
• دعم {total_coins:,}+ عملة
• تحديث فوري للأسعار
• تحليل SMC/ICT متقدم
• حساب القيمة التلقائي

*🔄 طريقة الاستخدام:*
• `/coin` - عرض عدد العملات المتاحة
• `BTC` - تحليل البيتكوين
• `5ETH` - حساب قيمة + تحليل
• `SHIB` - تحليل الميم كوين

🔔 *تابعنا:* {CHANNEL_LINK}
"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🪙 العملات الشائعة", callback_data="popular_coins"),
        InlineKeyboardButton("📚 شرح SMC/ICT", callback_data="explain_smc"),
        InlineKeyboardButton("📊 إحصائيات العملات", callback_data="coins_stats")
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['coin'])
def show_coins_count(message):
    total_coins = analyzer.coin_database.get_total_coins_count()
    
    response_text = f"""
📊 **إحصائيات قاعدة بيانات العملات**

• **إجمالي العملات المدعومة:** `{total_coins:,}` عملة
• **مصادر البيانات:** 3 APIs مختلفة
• **يشمل:** العملات الرئيسية + الميم كوين

🔍 **المصادر الرئيسية:**
• CoinGecko (300+ عملة)
• Binance (2,000+ عملة)
• العملات التاريخية (50+ عملة)

💡 **للبحث:** اكتب رمز العملة فقط مثل:
`BTC`, `ETH`, `SHIB`, `DOGE`
"""
    bot.send_message(message.chat.id, response_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        user_input = message.text.strip()
        
        # البحث عن العملات
        if len(user_input) <= 10:
            search_results = analyzer.coin_database.search_coin(user_input)
            if search_results:
                coin_data = search_results[0]
                coin_symbol = coin_data['symbol']
                
                # تحليل مباشر للعملة
                handle_coin_analysis(message, coin_symbol)
                return
        
        # معالجة الأوامر الأخرى
        handle_coin_analysis(message, user_input)
        
    except Exception as e:
        print(f"Error handling message: {e}")
        bot.reply_to(message, "❌ حدث خطأ في معالجة طلبك. حاول مرة أخرى.")

def handle_coin_analysis(message, user_input):
    """معالجة تحليل العملة"""
    try:
        # استخراج الكمية والعملة
        amount_match = re.match(r'^(\d*\.?\d+)?\s*([A-Za-z]+)$', user_input)
        if not amount_match:
            bot.reply_to(message, "❌ صيغة غير صحيحة. استخدم: `BTC` أو `5ETH`")
            return
        
        amount_str, coin_symbol = amount_match.groups()
        amount = float(amount_str) if amount_str else None
        coin_symbol = coin_symbol.upper()
        
        # جلب بيانات السوق
        market_data = analyzer.get_live_market_data(coin_symbol)
        if not market_data or not market_data.get('current_price'):
            bot.reply_to(message, f"❌ لم أتمكن من العثور على سعر {coin_symbol}")
            return
        
        # إظهار رسالة "جاري التحليل"
        processing_msg = bot.reply_to(message, f"🔄 جاري تحليل {coin_symbol}...")
        
        # جلب البيانات التاريخية وإنشاء الرسم البياني
        df = analyzer.get_historical_data_with_timeframe(coin_symbol, '4h', 30)
        if df is None or df.empty:
            bot.edit_message_text(f"❌ لا توجد بيانات تاريخية لـ {coin_symbol}", 
                                message.chat.id, processing_msg.message_id)
            return
        
        # إنشاء الرسم البياني
        chart_buffer, analysis_text = analyzer.create_smc_ict_chart(
            df, coin_symbol, market_data, '4h', amount
        )
        
        if chart_buffer:
            # إرسال الصورة مع التحليل
            bot.send_photo(
                message.chat.id,
                chart_buffer,
                caption=analysis_text,
                parse_mode='Markdown'
            )
            bot.delete_message(message.chat.id, processing_msg.message_id)
        else:
            bot.edit_message_text(
                f"❌ خطأ في إنشاء الرسم البياني لـ {coin_symbol}\n{analysis_text}",
                message.chat.id, processing_msg.message_id
            )
            
    except Exception as e:
        print(f"Analysis error: {e}")
        bot.reply_to(message, f"❌ حدث خطأ في تحليل العملة: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        if call.data == "popular_coins":
            show_popular_coins(call.message)
        elif call.data == "explain_smc":
            explain_smc_ict(call.message)
        elif call.data == "coins_stats":
            show_coins_stats(call.message)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Callback error: {e}")

def show_popular_coins(message):
    """عرض العملات الشائعة"""
    popular_coins = ['BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'DOGE', 'SOL', 'DOT', 'MATIC', 'SHIB']
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for coin in popular_coins:
        buttons.append(InlineKeyboardButton(coin, callback_data=f"analyze_{coin}"))
    
    keyboard.add(*buttons)
    
    text = "🪙 *العملات الرقمية الشائعة*\n\nاختر عملة للتحليل الفني:"
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')

def explain_smc_ict(message):
    """شرح SMC و ICT"""
    explanation = """
📚 *شرح SMC و ICT*

*🎯 SMC (Smart Money Concepts):*
• **FVG (Fair Value Gap):** مناطق عدم التوازن في السوق
• **Order Blocks:** مناطق دخول الأموال الذكية
• **Liquidity:** مناطق السيولة التي يستهدفها السوق

*🔍 ICT (Inner Circle Trader):*
• **Market Structure:** تحليل هيكل السوق
• **Support/Resistance:** مستويات الدعم والمقاومة
• **Price Action:** حركة السعر والأنماط

*💡 كيف تستخدم البوت:*
1. اكتب رمز العملة مثل `BTC`
2. البوت يحلل ويظهر FVG, OB, Liquidity
3. يعطيك توقعات وأهداف

🔔 *تابعنا:* @zforexms
"""
    bot.send_message(message.chat.id, explanation, parse_mode='Markdown')

def show_coins_stats(message):
    """عرض إحصائيات العملات"""
    total_coins = analyzer.coin_database.get_total_coins_count()
    
    stats_text = f"""
📊 **إحصائيات قاعدة البيانات**

• **إجمالي العملات:** `{total_coins:,}` عملة
• **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
• **المصادر:** CoinGecko, Binance, DexScreener

💡 **للبحث:** اكتب رمز العملة فقط
مثال: `BTC`, `ETH`, `SHIB`

🔔 **القناة:** {CHANNEL_LINK}
"""
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

# ==============================================
# 🚀 تشغيل البوت على Railway
# ==============================================

if __name__ == "__main__":
    print("🚀 بدء تشغيل البوت على Railway...")
    print(f"📊 قاعدة بيانات العملات: {analyzer.coin_database.get_total_coins_count():,} عملة")
    
    # إعداد webhook لـ Railway
    if WEBHOOK_URL:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
        print(f"🌐 Webhook مضبوط على: {WEBHOOK_URL}")
        
        # تشغيل الخادم
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
        def index():
            return "🚀 MS TRADING BOT is running on Railway!"
        
        # تشغيل الخادم على المنفذ المحدد من Railway
        app.run(host='0.0.0.0', port=PORT)
    else:
        # التشغيل المحلي (للتنمية)
        print("🔧 التشغيل في وضع Polling...")
        bot.infinity_polling()
