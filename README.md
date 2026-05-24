# 🤖 Super AI Bot — Ultimate Edition v3.0

Telegram uchun to'liq AI bot — ko'p model, vision, voice, RAG, premium, anti-spam va boshqalar.

---

## ✅ Imkoniyatlar

| Xususiyat | Tavsif |
|---|---|
| 🤖 Ko'p AI model | Gemini 1.5 Flash, ChatGPT-4o Mini, Groq LLaMA 3.3/4 |
| 🔄 Auto fallback | Model ishlamasa keyingisi avtomatik |
| 👁 Vision | Rasm tahlili (Gemini & GPT-4o) |
| 🎤 Voice-to-Text | Groq Whisper-large-v3 (bepul) |
| 🌐 Web Search | Gemini google_search (real vaqt) |
| 🖼 Rasm yaratish | DALL-E 3 + stil + O'zbek→Ingliz tarjima |
| 📄 RAG | PDF/TXT/DOCX/MD/CSV hujjat asosida javob |
| 🧵 Thread | Parallel nomlangan suhbatlar (max 10) |
| 🌍 Til | uz/ru/en (avtomatik sistem prompt) |
| ⚡ Inline | Guruhda `@bot savol` |
| 🔒 Anti-spam | Rate limiting + flood himoya |
| ⭐ Premium | Telegram Stars to'lov + kunlik limitlar |
| 🔔 Scheduler | Cron eslatmalar (daily/weekly/monthly) |
| 📊 Analytics | Kunlik faollik grafigi (ASCII) |
| 🌐 Webhook | Render.com uchun Flask server |
| 👑 Admin Panel | Gemini function calling bilan AI admin |
| 📱 Mini App | Telegram Web App (webapp/index.html) |

---

## 🚀 Lokal ishga tushirish

### 1. Loyihani klonlash
```bash
git clone https://github.com/mrmr18964-lgtm/sfdgn
cd sfdgn
```

### 2. Virtual muhit
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
# yoki
venv\Scripts\activate           # Windows
```

### 3. Kutubxonalar
```bash
pip install -r requirements.txt
```

### 4. .env fayl
```bash
cp .env.example .env
```
`.env` faylini oching va kalitlarni kiriting:

| Kalit | Qayerdan olish |
|---|---|
| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/BotFather) → /newbot |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) |
| `ADMIN_GEMINI_KEY` | Xuddi Gemini key (alohida yoki bir xil) |
| `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/) |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/) |
| `ADMIN_IDS` | Botga `/myid` yozing |

### 5. Ishga tushirish (lokal — polling)
```bash
python bot.py
```

---

## ☁️ Render.com ga deployment

### 1-usul: render.yaml bilan (tavsiya)

1. GitHub ga push qiling:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/mrmr18964-lgtm/sfdgn.git
git push -u origin main
```

2. [render.com](https://render.com) → **New** → **Web Service** → GitHub repo tanlang

3. Render avtomatik `render.yaml` ni o'qiydi

4. **Environment Variables** bo'limida kalitlarni kiriting:
   - `TELEGRAM_TOKEN`
   - `GEMINI_API_KEY`
   - `ADMIN_GEMINI_KEY`
   - `OPENAI_API_KEY`
   - `GROQ_API_KEY`
   - `ADMIN_IDS`
   - `WEBHOOK_URL` = `https://sfdgn.onrender.com`

5. **Deploy** tugmasini bosing

6. URL tayyor bo'lgach, `.env` ga yoki Render dashboard ga `WEBHOOK_URL` ni qo'shing

### Muhim: Persistent Disk
SQLite bazasi saqlanishi uchun Render da **Disk** qo'shing:
- Mount path: `/opt/render/project/src/data`
- Size: 1 GB (bepul reja uchun)

---

## 📱 Mini App (ixtiyoriy)

`webapp/index.html` ni HTTPS serverga joylashtiring:

**GitHub Pages:**
```bash
# webapp/ papkasini alohida repo yoki gh-pages branch ga
# URL: https://mrmr18964-lgtm.github.io/bot-webapp/
```

**Vercel:**
```bash
npm i -g vercel
cd webapp
vercel --prod
```

Keyin `.env` ga:
```
BOT_WEBAPP_URL=https://your-webapp-url.com/index.html
```

---

## 📱 Bot buyruqlari

| Buyruq | Tavsif |
|---|---|
| `/start` | Botni boshlash |
| `/model` | AI modelni tanlash |
| `/lang` | Til (uz/ru/en) |
| `/thread` | Thread boshqaruvi |
| `/docs` | Hujjatlar (RAG) |
| `/image` | Rasm yaratish rejimi |
| `/chat` | Suhbat rejimine qaytish |
| `/voice` | Ovoz javob yoq/o'chir |
| `/clear` | Thread tarixini tozalash |
| `/remind YYYY-MM-DD HH:MM [repeat] matn` | Eslatma qo'shish |
| `/schedules` | Eslatmalar ro'yxati |
| `/premium` | Premium obuna |
| `/status` | Joriy holat |
| `/myid` | Telegram ID |
| `/admin` | Admin panel (faqat adminlar) |
| `/analytics` | Analytics (faqat adminlar) |

### Eslatma misollari:
```
/remind 2025-12-31 09:00 Yangi yil tabriknomasi
/remind 2025-06-01 08:00 daily Har kuni ertalab xabar
/remind 2025-06-01 09:00 weekly Haftalik hisobot
/remind 2025-06-01 10:00 monthly Oylik to'lov
```

---

## ⭐ Premium tizimi

- **Bepul:** 30 xabar/kun, 5 rasm/kun
- **Premium:** Cheksiz (100 Telegram Stars/oy)

Admin premium berish:
```
# Admin panelda:
@username ga 1 oylik premium ber
@username ga 3 oylik premium ber
```

---

## 🔒 Xavfsizlik

- Barcha API kalitlar `.env` da (hech qachon koda ichida emas)
- `.gitignore` `.env` ni git dan chiqarib qo'yadi
- Webhook `SECRET_TOKEN` bilan himoyalangan (SHA-256)
- Anti-spam: 10 xabar/60 soniya limit
- SQL injection himoyasi: parametrlangan so'rovlar
- XSS himoyasi: input sanitizatsiya
- Rate limit bloklash: 30 soniya

---

## 📁 Fayl strukturasi

```
super-ai-bot/
├── bot.py              # Asosiy bot kodi
├── requirements.txt    # Python kutubxonalar
├── render.yaml         # Render.com konfiguratsiya
├── Procfile            # Process fayli
├── .env.example        # Muhit o'zgaruvchilari namunasi
├── .gitignore          # Git ignore
├── README.md           # Ushbu fayl
└── webapp/
    └── index.html      # Telegram Mini App
```

---

## 🛠 Muammolar va yechimlar

**Bot javob bermayapti:**
- `TELEGRAM_TOKEN` to'g'riligini tekshiring
- Render loglarini ko'ring: Dashboard → Logs

**Webhook ishlamayapti:**
- `WEBHOOK_URL` https:// bilan boshlanishini tekshiring
- Bot Webhook ni qayta o'rnating: `bot.remove_webhook()` keyin qayta run

**Gemini rate limit:**
- Bot avtomatik `gemini-1.5-flash-8b` ga o'tadi
- Kerak bo'lsa boshqa model tanlang: `/model`

**SQLite yo'qoldi:**
- Render free plan restart qilganda disk tozalanadi
- Render Disk qo'shing (persistent storage)

---

## 📞 Qo'llab-quvvatlash

Admin panelda: `statistika ko'rsat`, `analytics 7 kun`
