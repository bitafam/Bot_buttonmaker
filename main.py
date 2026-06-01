from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
import os

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()
app = FastAPI()

user_data = {}

# ================== start ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 سلام! پستت رو (متن، عکس، ویدیو...) اینجا بفرست.")

@dp.message()
async def handle_post(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id] = {"message": message, "buttons": []}
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه", callback_data="add_button")],
        [InlineKeyboardButton(text="📤 ارسال به کانال", callback_data="send_to_channel")]
    ])
    await message.answer("✅ پست دریافت شد!\nحالا دکمه اضافه کن یا ارسال کن:", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "add_button")
async def add_button(callback: types.CallbackQuery):
    await callback.message.answer("📌 فرمت:\n`متن دکمه | لینک`\nمثال:\n`سایت | https://google.com`")
    user_data[callback.from_user.id]["step"] = "waiting_button"

@dp.message(lambda m: user_data.get(m.from_user.id, {}).get("step") == "waiting_button")
async def save_button(message: types.Message):
    user_id = message.from_user.id
    try:
        text, url = [x.strip() for x in message.text.split("|", 1)]
        if not url.startswith("http"): url = "https://" + url
        user_data[user_id]["buttons"].append({"text": text, "url": url})
        
        btns = "\n".join([f"• {b['text']} → {b['url']}" for b in user_data[user_id]["buttons"]])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ دکمه جدید", callback_data="add_button")],
            [InlineKeyboardButton(text="📤 ارسال به کانال", callback_data="send_to_channel")]
        ])
        await message.answer(f"✅ دکمه اضافه شد!\n\nدکمه‌ها:\n{btns}", reply_markup=kb)
        user_data[user_id]["step"] = None
    except:
        await message.answer("❌ فرمت اشتباه! مثال: `متن | لینک`")

@dp.callback_query(lambda c: c.data == "send_to_channel")
async def send_to_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_data.get(user_id)
    if not data: return await callback.answer("خطا! دوباره پست بفرست.", show_alert=True)
    
    original = data["message"]
    buttons = data["buttons"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=b["text"], url=b["url"])] for b in buttons]) if buttons else None
    
    try:
        if original.text:
            await bot.send_message(CHANNEL_ID, original.text, reply_markup=keyboard)
        elif original.photo:
            await bot.send_photo(CHANNEL_ID, original.photo[-1].file_id, caption=original.caption or "", reply_markup=keyboard)
        elif original.video:
            await bot.send_video(CHANNEL_ID, original.video.file_id, caption=original.caption or "", reply_markup=keyboard)
        elif original.document:
            await bot.send_document(CHANNEL_ID, original.document.file_id, caption=original.caption or "", reply_markup=keyboard)
        await callback.answer("✅ به کانال ارسال شد!", show_alert=True)
    except Exception as e:
        await callback.answer(f"خطا: {str(e)}", show_alert=True)

# ================== Webhook ==================
@app.post("/webhook")
async def webhook(request: Request):
    update = types.Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        await bot.set_webhook(webhook_url)
        print("Webhook تنظیم شد!")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
