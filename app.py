from flask import Flask, render_template, request, jsonify, session
from tradingview_ta import TA_Handler, Interval
import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_trading_key_153'

VIP_PASSWORD = "VIP153"

FOREX_PAIRS = {
    'EUR/USD': 'EURUSD',
    'GBP/USD': 'GBPUSD',
    'USD/JPY': 'USDJPY',
    'AUD/USD': 'AUDUSD',
    'USD/CAD': 'USDCAD',
    'USD/CHF': 'USDCHF',
    'NZD/USD': 'NZDUSD',
    'EUR/GBP': 'EURGBP',
    'EUR/JPY': 'EURJPY',
    'GBP/JPY': 'GBPJPY',
    'AUD/JPY': 'AUDJPY',
    'EUR/AUD': 'EURAUD'
}

def get_interval(tf_str):
    mapping = {
        '1m': Interval.INTERVAL_1_MINUTE,
        '5m': Interval.INTERVAL_5_MINUTES,
        '15m': Interval.INTERVAL_15_MINUTES,
        '30m': Interval.INTERVAL_30_MINUTES,
        '1h': Interval.INTERVAL_1_HOUR,
        '1d': Interval.INTERVAL_1_DAY
    }
    return mapping.get(tf_str, Interval.INTERVAL_1_MINUTE)

@app.route('/')
def home():
    if 'signal_count' not in session:
        session['signal_count'] = 0
        session['last_reset'] = datetime.datetime.now().isoformat()
    if 'is_vip' not in session:
        session['is_vip'] = False
        
    return render_template('index.html', pairs=FOREX_PAIRS, is_vip=session.get('is_vip', False))

@app.route('/verify-vip', methods=['POST'])
def verify_vip():
    data = request.get_json(silent=True) or {}
    entered_pass = data.get('vip_pass', '')
    if entered_pass == VIP_PASSWORD:
        session['is_vip'] = True
        return jsonify({
            'status': 'success',
            'msg_bn': 'অভিনন্দন! আপনার VIP পাসওয়ার্ডটি ভ্যালিড। VIP এক্সেস সক্রিয় হয়েছে।',
            'msg_en': 'Success! Valid VIP Password. Access Granted.'
        })
    else:
        return jsonify({
            'status': 'invalid',
            'msg_bn': '❌ ইনভ্যালিড পাসওয়ার্ড! সঠিক পাসওয়ার্ডের জন্য টেলিগ্রামে যোগাযোগ করুন।',
            'msg_en': 'Invalid VIP Password! Contact admin on Telegram for access.'
        })

@app.route('/analyze', methods=['POST'])
def analyze():
    now = datetime.datetime.now()
    last_reset_str = session.get('last_reset', now.isoformat())
    try:
        last_reset = datetime.datetime.fromisoformat(last_reset_str)
    except ValueError:
        last_reset = now

    if (now - last_reset).total_seconds() >= 86400:
        session['signal_count'] = 0
        session['last_reset'] = now.isoformat()

    is_vip = session.get('is_vip', False)
    signal_count = session.get('signal_count', 0)

    if not is_vip and signal_count >= 5:
        return jsonify({
            'status': 'limit_reached',
            'msg_bn': 'আপনার আজকের ফ্রি ৫টি সিগন্যাল লিমিট শেষ। VIP পাসওয়ার্ড দিয়ে আনলিমিটেড ব্যবহার করুন।',
            'msg_en': 'Free daily limit reached. Enter VIP Password for unlimited access.'
        })

    data = request.get_json(silent=True) or {}
    pair_symbol = data.get('pair')
    timeframe = data.get('timeframe', '1m')

    if not pair_symbol or pair_symbol not in FOREX_PAIRS:
        return jsonify({
            'status': 'error',
            'msg_bn': 'অনুগ্রহ করে একটি সঠিক কারেন্সি পেয়ার নির্বাচন করুন।',
            'msg_en': 'Please select a valid currency pair.'
        })

    try:
        handler = TA_Handler(
            symbol=FOREX_PAIRS[pair_symbol],
            screener="forex",
            exchange="FX_IDC",
            interval=get_interval(timeframe)
        )
        analysis = handler.get_analysis()
        summary = analysis.summary
        indicators = analysis.indicators

        current_price = indicators.get('close', 0.0)
        recommendation = summary.get('RECOMMENDATION', 'NEUTRAL')

        if 'BUY' in recommendation:
            pa_zone = f"Support Rejection Zone ({round(current_price * 0.9995, 5)})"
            signal_type = "STRONG BUY 🟢"
        elif 'SELL' in recommendation:
            pa_zone = f"Resistance Rejection Zone ({round(current_price * 1.0005, 5)})"
            signal_type = "STRONG SELL 🔴"
        else:
            pa_zone = "Consolidation Zone / Wait for Breakout"
            signal_type = "NEUTRAL ⚪"

        if not is_vip:
            session['signal_count'] = signal_count + 1

        remaining = "আনলিমিটেড" if is_vip else f"{5 - session['signal_count']} টি"

        return jsonify({
            'status': 'success',
            'pair': pair_symbol,
            'signal_type': signal_type,
            'entry_price': current_price,
            'pa_zone': pa_zone,
            'timeframe': timeframe,
            'remaining': remaining,
            'msg_bn': 'প্রাইস অ্যাকশন সিগন্যাল প্রস্তুত!',
            'msg_en': 'Price Action Signal Generated!'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'msg_bn': 'মার্কেট ডাটা আনতে সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।',
            'msg_en': 'Error fetching market data. Please try again.'
        })

if __name__ == '__main__':
    app.run(debug=True)
