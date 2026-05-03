import logging
import asyncio
import aiohttp
import urllib.parse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === TOKEN ===
TELEGRAM_TOKEN = "8764046303:AAHqWzFEOI8o3A4FGdktm1ew1MycESsgQdk"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================== GÖRSEL ÜRETİM ========================
async def generate_image(prompt: str) -> bytes:
    """Pollinations.ai ile görsel üret (ücretsiz, anahtar gerekmez)"""
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=60) as resp:
            if resp.status == 200:
                return await resp.read()
            raise Exception(f"Görsel üretilemedi: HTTP {resp.status}")

# ======================== SOHBET AI'ları ========================
async def call_pollinations(prompt: str) -> str:
    url = f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=30) as resp:
            if resp.status == 200:
                return await resp.text()
            raise Exception(f"Pollinations: HTTP {resp.status}")

async def call_groq(prompt: str) -> str:
    api_key = "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"
    if not api_key: return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "mixtral-8x7b-32768", "messages": [{"role": "user", "content": prompt}]}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    return None

async def call_gemini(prompt: str) -> str:
    api_key = "AIzaSyCNU8Hqo96-xkdnlM8gWevUCowIsl0LINc"
    if not api_key: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
    return None

async def call_openrouter(prompt: str) -> str:
    api_key = "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"
    if not api_key: return None
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "meta-llama/llama-3.3-70b-instruct:free", "messages": [{"role": "user", "content": prompt}]}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    return None

# ======================== VENICE.AI (EKLENDİ) ========================
async def call_venice(prompt: str) -> str:
    api_key = "VENICE_INFERENCE_KEY_eqIm54tblIewJQ84MaIXwb5qYia_QOEzHLiOhrMP_N"
    if not api_key:
        return None
    url = "https://api.venice.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "venice-uncensored",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
            if resp.status == 200:
                data = await resp.json()
                # Venice yanıtı OpenAI formatında
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"]
            logger.warning(f"Venice API hatası: {resp.status}")
            return None

# ======================== ANA SOHBET YÖNLENDİRİCİ ========================
async def ask_ai(prompt: str, preferred: str = None) -> str:
    if preferred == "groq":
        res = await call_groq(prompt)
        if res: return res
    if preferred == "gemini":
        res = await call_gemini(prompt)
        if res: return res
    if preferred == "openrouter":
        res = await call_openrouter(prompt)
        if res: return res
    if preferred == "venice":
        res = await call_venice(prompt)
        if res: return res
    # Yedek olarak Pollinations
    return await call_pollinations(prompt)

# ======================== TELEGRAM KOMUTLARI ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Çoklu AI Asistanı + Görsel Üretim + Venice*\n\n"
        "📝 *Sohbet için:*\n"
        "• `/setai groq` - Groq (hızlı)\n"
        "• `/setai gemini` - Google Gemini\n"
        "• `/setai openrouter` - OpenRouter (Llama 3.3)\n"
        "• `/setai venice` - Venice.ai (uncensored)\n"
        "• `/setai pollinations` - Pollinations (yedek)\n\n"
        "🎨 *Görsel üretmek için:*\n"
        "• `/image <açıklama>` - Örn: `/image kırmızı elma ağaçta`\n\n"
        "Önce bir AI seç, sonra sohbet et. Görsel için /image kullan.",
        parse_mode="Markdown"
    )

async def set_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Kullanım: `/setai <groq|gemini|openrouter|venice|pollinations>`")
        return
    choice = context.args[0].lower()
    valid = ["groq", "gemini", "openrouter", "venice", "pollinations"]
    if choice not in valid:
        await update.message.reply_text(f"Geçersiz. Geçerli: {', '.join(valid)}")
        return
    context.user_data["preferred_ai"] = choice
    await update.message.reply_text(f"✅ Sohbet AI tercihin **{choice}** olarak ayarlandı!")

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🎨 Kullanım: `/image <açıklama>`\nÖrnek: `/image uzayda uçan roket`")
        return
    prompt = " ".join(context.args)
    loading = await update.message.reply_text("🎨 Görsel üretiliyor, lütfen bekleyin...")
    try:
        img_bytes = await generate_image(prompt)
        await update.message.reply_photo(photo=img_bytes, caption=f"👉 {prompt}")
        await loading.delete()
    except Exception as e:
        await loading.edit_text(f"❌ Hata: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or update.message.text.startswith('/'):
        return
    prompt = update.message.text
    preferred = context.user_data.get("preferred_ai")
    await update.message.reply_chat_action(action="typing")
    try:
        response = await ask_ai(prompt, preferred)
        # Mesaj gönderimi sırasında oluşabilecek "Message to be replied not found" hatasını engellemek için
        # doğrudan send_message kullanıyoruz. reply_text bazen sorun çıkarabiliyor.
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response[:4096])
    except Exception as e:
        logger.error(f"Sohbet hatası: {e}")
        try:
            # Yedek olarak Pollinations'ı dene
            fallback_response = await call_pollinations(prompt)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Yedek AI (Pollinations) yanıtı:\n{fallback_response[:4096]}")
        except Exception as fallback_error:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Şu anda cevap veremiyorum. Lütfen daha sonra tekrar deneyin.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setai", set_ai))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot çalışıyor! /start ile başla, /image ile görsel üret.")
    app.run_polling()

if __name__ == "__main__":
    main()
