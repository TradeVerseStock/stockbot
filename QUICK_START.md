# ⚡ Quick Start — Run Bot in 10 Minutes (FREE)

---

## You need ONLY 1 thing: Your Telegram Bot Token

---

## STEP 1 — Edit bot_free.py

Open `bot_free.py` and find line 9:
```python
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
```
Replace with your actual token. Example:
```python
TELEGRAM_TOKEN = "5876543210:AAFxyz_abcdefghijklmnopqrstuvwxyz"
```

---

## STEP 2 — Run on Railway.app (100% FREE)

### 2a. Upload to GitHub
1. Go to **github.com** → Sign up (free)
2. Click **New Repository** → Name it `stockbot`
3. Upload these 3 files:
   - `bot_free.py` → rename to `bot.py`
   - `requirements.txt`
   - Create a new file called `Procfile` with content:
     ```
     worker: python bot.py
     ```

### 2b. Deploy on Railway
1. Go to **railway.app** → Sign up with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Select your `stockbot` repo
4. Railway auto-deploys! ✅
5. Your bot is now running 24/7 for FREE

---

## OR — Run on Your PC (for testing only)

### Install Python first:
Download from: https://python.org/downloads
(Choose Python 3.10 or 3.11)

### Then run these commands:
```bash
pip install python-telegram-bot yfinance pandas razorpay
python bot_free.py
```

Bot will start! Open Telegram → find your bot → send `/start`

---

## STEP 3 — Test Your Bot

1. Open Telegram
2. Search for your bot name
3. Send `/start`
4. Type `RELIANCE` → Get full analysis! 🎉

---

## When Razorpay Approves (switch to paid version):

1. Open `bot.py` (the paid version)
2. Fill in your tokens:
   - `TELEGRAM_TOKEN` (same as now)
   - `RAZORPAY_KEY_ID`
   - `RAZORPAY_SECRET`
3. Replace `bot_free.py` with `bot.py` on Railway
4. Done! Now collecting payments 💰

---

## Promote Your Bot Now (while waiting for KYC):

Share this message in stock market WhatsApp/Telegram groups:

> 🚀 *Free Stock Analysis Bot!*
> Get complete Fundamental + Technical analysis of any NSE/BSE stock in seconds!
> 
> ✅ RSI, MACD, Bollinger Bands
> ✅ P/E, P/B, EPS, ROE and more
> ✅ Support & Resistance levels
> ✅ Overall Buy/Sell signal
> 
> 👉 [Your Bot Link Here]
> 
> 100% FREE right now — try it!

---

## 💡 Pro Tip

Keep a note of your bot's user count in Railway logs.
When Razorpay approves and you switch to paid version,
you'll already have hundreds of users ready to convert!
