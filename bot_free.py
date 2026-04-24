import logging
import sqlite3
from datetime import datetime
import yfinance as yf
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ─── CONFIG — ONLY CHANGE THIS ─────────────────────────────────────────────────
TELEGRAM_TOKEN = "8782200688:AAGRYOVMnb4yUjPq2DF8onEoV8iQlhM4oMY"   # ← Paste your token here

BOT_NAME       = "StockBot Pro"
FREE_LIMIT     = 10   # searches per day for free users (set high for testing)
# ───────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── DATABASE ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id          INTEGER PRIMARY KEY,
            username         TEXT,
            first_name       TEXT,
            joined_at        TEXT,
            total_searches   INTEGER DEFAULT 0,
            daily_count      INTEGER DEFAULT 0,
            last_search_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def ensure_user(user_id, username, first_name):
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
        VALUES (?,?,?,?)
    """, (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def can_search(user_id):
    row = get_user(user_id)
    if not row:
        return True, FREE_LIMIT
    today = datetime.now().strftime("%Y-%m-%d")
    if row[6] != today:
        conn = sqlite3.connect("bot_data.db")
        c = conn.cursor()
        c.execute("UPDATE users SET daily_count=0, last_search_date=? WHERE user_id=?", (today, user_id))
        conn.commit()
        conn.close()
        return True, FREE_LIMIT
    remaining = FREE_LIMIT - row[5]
    return remaining > 0, max(0, remaining)

def increment_search(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("""
        UPDATE users
        SET daily_count=daily_count+1,
            total_searches=total_searches+1,
            last_search_date=?
        WHERE user_id=?
    """, (today, user_id))
    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

# ─── STOCK ANALYSIS ────────────────────────────────────────────────────────────
def get_ticker(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        symbol += ".NS"
    return symbol

def analyze_stock(symbol: str) -> str:
    ticker_sym = get_ticker(symbol)
    stock = yf.Ticker(ticker_sym)
    info = stock.info

    if not info or info.get("regularMarketPrice") is None:
        ticker_sym = symbol.upper().strip() + ".BO"
        stock = yf.Ticker(ticker_sym)
        info = stock.info
        if not info or info.get("regularMarketPrice") is None:
            return (
                f"❌ *Stock not found:* `{symbol.upper()}`\n\n"
                f"Please check the symbol. Examples:\n"
                f"`RELIANCE` `TCS` `INFY` `HDFCBANK` `SBIN`\n"
                f"`WIPRO` `ICICIBANK` `BAJFINANCE` `ITC` `LT`"
            )

    hist = stock.history(period="6mo")
    if hist.empty:
        return "❌ Could not fetch historical data. Try again."

    # ── Price Info ──
    name       = info.get("longName", symbol)
    price      = info.get("regularMarketPrice") or info.get("currentPrice", 0)
    prev_close = info.get("regularMarketPreviousClose", 0)
    change     = round(price - prev_close, 2) if price and prev_close else 0
    change_pct = round((change / prev_close) * 100, 2) if prev_close else 0
    week52h    = info.get("fiftyTwoWeekHigh", "N/A")
    week52l    = info.get("fiftyTwoWeekLow", "N/A")
    sector     = info.get("sector", "N/A")
    industry   = info.get("industry", "N/A")

    # ── Fundamental ──
    market_cap = info.get("marketCap", None)
    pe         = info.get("trailingPE", "N/A")
    pb         = info.get("priceToBook", "N/A")
    eps        = info.get("trailingEps", "N/A")
    roe        = info.get("returnOnEquity", None)
    roe        = f"{round(roe*100,2)}%" if roe else "N/A"
    debt_eq    = info.get("debtToEquity", "N/A")
    profit_mg  = info.get("profitMargins", None)
    profit_mg  = f"{round(profit_mg*100,2)}%" if profit_mg else "N/A"
    div_yield  = info.get("dividendYield", None)
    div_yield  = f"{round(div_yield*100,2)}%" if div_yield else "N/A"
    revenue    = info.get("totalRevenue", None)
    net_income = info.get("netIncomeToCommon", None)
    beta       = info.get("beta", "N/A")
    book_val   = info.get("bookValue", "N/A")

    def fmt_crore(val):
        if isinstance(val, (int, float)):
            crore = val / 1e7
            if crore >= 1e5:
                return f"₹{round(crore/1e5,2):,} Lakh Cr"
            return f"₹{round(crore,2):,} Cr"
        return "N/A"

    def fp(val):
        return f"₹{val:,.2f}" if isinstance(val, (int, float)) else str(val)

    # ── Technical ──
    close  = hist["Close"]
    volume = hist["Volume"]

    ma20  = round(close.rolling(20).mean().iloc[-1], 2)
    ma50  = round(close.rolling(50).mean().iloc[-1], 2) if len(close) >= 50 else None
    ma200 = round(close.rolling(200).mean().iloc[-1], 2) if len(close) >= 200 else None

    # RSI
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rsi   = round(100 - (100 / (1 + gain.iloc[-1] / loss.iloc[-1])), 2) if loss.iloc[-1] != 0 else 50

    # MACD
    ema12      = close.ewm(span=12).mean()
    ema26      = close.ewm(span=26).mean()
    macd_line  = ema12 - ema26
    sig_line   = macd_line.ewm(span=9).mean()
    macd_val   = round(macd_line.iloc[-1], 2)
    sig_val    = round(sig_line.iloc[-1], 2)
    macd_hist  = round(macd_val - sig_val, 2)

    # Bollinger Bands
    std20      = close.rolling(20).std()
    bb_upper   = round((close.rolling(20).mean() + 2*std20).iloc[-1], 2)
    bb_lower   = round((close.rolling(20).mean() - 2*std20).iloc[-1], 2)
    bb_mid     = ma20

    # Support / Resistance
    support    = round(close.tail(20).min(), 2)
    resistance = round(close.tail(20).max(), 2)

    # Volume
    avg_vol  = int(volume.rolling(20).mean().iloc[-1])
    cur_vol  = int(volume.iloc[-1])
    vol_chg  = round((cur_vol - avg_vol) / avg_vol * 100, 1) if avg_vol else 0

    # Stochastic %K
    low14  = hist["Low"].rolling(14).min()
    high14 = hist["High"].rolling(14).max()
    stoch  = round(((hist["Close"] - low14) / (high14 - low14) * 100).iloc[-1], 2)

    # ── Signal Interpretation ──
    arrow       = "🟢 ▲" if change >= 0 else "🔴 ▼"
    rsi_sig     = "🔴 Overbought — Caution!" if rsi > 70 else ("🟢 Oversold — Opportunity?" if rsi < 30 else "🟡 Neutral Zone")
    macd_sig    = "🟢 Bullish Crossover" if macd_val > sig_val else "🔴 Bearish Crossover"
    macd_mom    = "↑ Gaining" if macd_hist > 0 else "↓ Losing"
    stoch_sig   = "🔴 Overbought" if stoch > 80 else ("🟢 Oversold" if stoch < 20 else "🟡 Neutral")

    if price >= bb_upper:
        bb_pos = "⚠️ Above Upper Band — Overbought"
    elif price <= bb_lower:
        bb_pos = "✅ Below Lower Band — Oversold"
    else:
        bb_pos = "✅ Within Bands — Normal"

    if ma50:
        trend = "🟢 Bullish" if price > ma50 else "🔴 Bearish"
    else:
        trend = "🟢 Bullish" if price > ma20 else "🔴 Bearish"

    vol_sig = "📈 High Volume" if cur_vol > avg_vol * 1.5 else ("📉 Low Volume" if cur_vol < avg_vol * 0.5 else "➡️ Normal Volume")

    # ── Overall Signal ──
    bull_signals = sum([
        change >= 0,
        rsi < 70,
        macd_val > sig_val,
        price > ma20,
        ma50 and price > ma50,
        stoch < 80,
        cur_vol > avg_vol,
    ])
    overall = "🟢 BULLISH" if bull_signals >= 5 else ("🔴 BEARISH" if bull_signals <= 2 else "🟡 NEUTRAL / SIDEWAYS")

    report = f"""
📊 *{name}*
🏷 `{ticker_sym}` | {sector}

━━━━━━━━━━━━━━━━━━
💰 *PRICE*
• Price    : *{fp(price)}*
• Change   : {arrow} {fp(change)} ({change_pct}%)
• 52W High : {fp(week52h)}
• 52W Low  : {fp(week52l)}
• Industry : {industry}

━━━━━━━━━━━━━━━━━━
📈 *FUNDAMENTAL ANALYSIS*
• Market Cap    : {fmt_crore(market_cap)}
• P/E Ratio     : {pe}
• P/B Ratio     : {pb}
• EPS           : {eps}
• Book Value    : {book_val}
• ROE           : {roe}
• Debt/Equity   : {debt_eq}
• Profit Margin : {profit_mg}
• Dividend Yield: {div_yield}
• Beta (Risk)   : {beta}
• Revenue       : {fmt_crore(revenue)}
• Net Income    : {fmt_crore(net_income)}

━━━━━━━━━━━━━━━━━━
📉 *TECHNICAL ANALYSIS*
• Trend   : {trend}
• MA 20   : {fp(ma20)}
• MA 50   : {fp(ma50) if ma50 else 'N/A (insufficient data)'}
• MA 200  : {fp(ma200) if ma200 else 'N/A (insufficient data)'}

🔷 *RSI (14)*: {rsi}
   → {rsi_sig}

🔷 *MACD*
   • MACD   : {macd_val}
   • Signal : {sig_val}
   • Hist   : {macd_hist} ({macd_mom} momentum)
   → {macd_sig}

🔷 *Stochastic %K*: {stoch}
   → {stoch_sig}

📐 *BOLLINGER BANDS*
   • Upper : {fp(bb_upper)}
   • Mid   : {fp(bb_mid)}
   • Lower : {fp(bb_lower)}
   → {bb_pos}

🎯 *SUPPORT & RESISTANCE* (20-day)
   • Support    : {fp(support)}
   • Resistance : {fp(resistance)}

📦 *VOLUME*
   • Today   : {cur_vol:,}
   • Avg 20d : {avg_vol:,}
   • Change  : {vol_chg:+}% → {vol_sig}

━━━━━━━━━━━━━━━━━━
🏁 *OVERALL SIGNAL*
   *{overall}*
   ({bull_signals}/7 bullish indicators)

━━━━━━━━━━━━━━━━━━
🤖 _{BOT_NAME}_
⚠️ _Not financial advice. DYOR._
"""
    return report.strip()

# ─── HANDLERS ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username or "", user.first_name)
    total = get_total_users()

    keyboard = [
        [InlineKeyboardButton("📊 Analyze a Stock", callback_data="how_to")],
        [InlineKeyboardButton("ℹ️ How to Use",       callback_data="how_to")],
        [InlineKeyboardButton("📈 Popular Stocks",    callback_data="popular")],
    ]
    await update.message.reply_text(
        f"👋 Welcome *{user.first_name}!*\n\n"
        f"🚀 *{BOT_NAME}* — Indian Stock Analyzer\n\n"
        f"Simply send any *NSE/BSE stock symbol* and get:\n\n"
        f"📈 *Fundamental Analysis*\n"
        f"  P/E, P/B, EPS, ROE, Debt/Equity, Revenue...\n\n"
        f"📉 *Technical Analysis*\n"
        f"  RSI, MACD, Bollinger Bands, MA 20/50/200...\n\n"
        f"🎯 *Signals & Summary*\n"
        f"  Overall Bullish/Bearish verdict\n\n"
        f"👥 {total} traders using this bot\n\n"
        f"Try now → just type: `RELIANCE`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "how_to":
        await query.edit_message_text(
            "ℹ️ *How to Use*\n\n"
            "Just type any stock symbol and send!\n\n"
            "*NSE Examples:*\n"
            "`RELIANCE` `TCS` `INFY` `HDFCBANK`\n"
            "`SBIN` `WIPRO` `ITC` `LT` `AXISBANK`\n\n"
            "*More Examples:*\n"
            "`BAJFINANCE` `ICICIBANK` `HINDUNILVR`\n"
            "`MARUTI` `TATAMOTORS` `ADANIENT`\n\n"
            "🔍 Just type the symbol — that's it!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ])
        )

    elif query.data == "popular":
        keyboard = [
            [
                InlineKeyboardButton("RELIANCE", callback_data="stock_RELIANCE"),
                InlineKeyboardButton("TCS",      callback_data="stock_TCS"),
            ],
            [
                InlineKeyboardButton("INFY",     callback_data="stock_INFY"),
                InlineKeyboardButton("HDFCBANK", callback_data="stock_HDFCBANK"),
            ],
            [
                InlineKeyboardButton("SBIN",     callback_data="stock_SBIN"),
                InlineKeyboardButton("ITC",      callback_data="stock_ITC"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="back")],
        ]
        await query.edit_message_text(
            "📈 *Popular Stocks — Tap to Analyze:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("stock_"):
        symbol = query.data.replace("stock_", "")
        await query.edit_message_text(f"🔍 Analyzing *{symbol}*... ⏳", parse_mode="Markdown")
        try:
            report = analyze_stock(symbol)
            await query.edit_message_text(report, parse_mode="Markdown")
        except Exception as e:
            logger.error(e)
            await query.edit_message_text("❌ Error fetching data. Please try again.")

    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("📊 Analyze a Stock", callback_data="how_to")],
            [InlineKeyboardButton("ℹ️ How to Use",       callback_data="how_to")],
            [InlineKeyboardButton("📈 Popular Stocks",    callback_data="popular")],
        ]
        await query.edit_message_text(
            f"🏠 *{BOT_NAME} — Home*\n\nType any stock symbol to analyze!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username or "", user.first_name)
    symbol = update.message.text.strip().upper()

    if symbol.startswith("/"):
        return

    allowed, remaining = can_search(user.id)
    if not allowed:
        await update.message.reply_text(
            f"⏰ *Daily limit reached!*\n\n"
            f"You've used your {FREE_LIMIT} free searches today.\n"
            f"Limit resets at midnight 🕛\n\n"
            f"_Premium plans coming soon with unlimited access!_",
            parse_mode="Markdown"
        )
        return

    increment_search(user.id)
    msg = await update.message.reply_text(
        f"🔍 Analyzing *{symbol}*...\nFetching live data ⏳",
        parse_mode="Markdown"
    )

    try:
        report = analyze_stock(symbol)
        await msg.edit_text(report, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error for {symbol}: {e}")
        await msg.edit_text(
            f"❌ Could not analyze `{symbol}`.\n\n"
            f"• Check the symbol is correct\n"
            f"• Try again in a moment\n"
            f"• Example: `RELIANCE` `TCS` `INFY`",
            parse_mode="Markdown"
        )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📖 *{BOT_NAME} — Help*\n\n"
        f"Send any NSE/BSE stock symbol to get full analysis.\n\n"
        f"*Commands:*\n"
        f"/start — Home\n"
        f"/help  — This message\n"
        f"/stats — Bot statistics\n\n"
        f"*Example stocks:*\n"
        f"`RELIANCE` `TCS` `INFY` `HDFCBANK` `SBIN`",
        parse_mode="Markdown"
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = get_total_users()
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total Users : {total}\n"
        f"⚡ Status      : 🟢 Online\n"
        f"🕒 Updated     : {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
        parse_mode="Markdown"
    )

# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stock))

    logger.info(f"🚀 {BOT_NAME} is LIVE!")
    app.run_polling()

if __name__ == "__main__":
    main()
