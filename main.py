from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Request
import os

TOKEN = os.getenv("BOT_TOKEN")

# 👥 دریافت لیست ادمین‌ها از رندر و تبدیل به لیست عددی پایتون
# مثال در رندر: 1111111,2222222,3333333
ADMINS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_STR.split(",") if x.strip().isdigit()]

# 📢 دریافت لیست کانال‌ها از رندر
# مثال در رندر: @chan1,-100222222,@chan3
CHANNELS_STR = os.getenv("CHANNEL_IDS", "")
CHANNEL_IDS = [x.strip() for x in CHANNELS_STR.split(",") if x.strip()]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
app = FastAPI()

# 🗄️ دیتابیس موقت در حافظه سرور
user_data = {}

# ================== دستور /start ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    # 🔒 قفل اختصاصی ادمین‌ها
    if user_id not in ADMIN_IDS:
        await message.answer("❌ شما دسترسی به این ربات شخصی را ندارید.")
        return

    # تعریف دیتای اولیه کاربر در صورت عدم وجود
    if user_id not in user_data:
        user_data[user_id] = {"message": None, "buttons": [], "layout": "single", "step": None, "target_channel": None}

    # اگر کانالی ست نشده باشد، اولین کانال لیست به صورت پیش‌فرض انتخاب می‌شود
    if not user_data[user_id].get("target_channel") and CHANNEL_IDS:
        user_data[user_id]["target_channel"] = CHANNEL_IDS[0]

    current_channel = user_data[user_id]["target_channel"]

    text = (
        "👋 سلام رئیس! به ربات پست‌ساز پیشرفته خوش آمدی.\n\n"
        f"📢 کانال فعلی برای ارسال: <b>{current_channel}</b>\n\n"
        "📝 همین الان **متن یا رسانه (عکس، ویدیو، فایل)** خودت رو بفرست تا بریم برای ساخت پست."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تغییر کانال هدف", callback_data="change_channel")]
    ])
        
    await message.answer(text, reply_markup=kb)

# ================== بخش مدیریت و تغییر کانال ==================
@dp.callback_query(lambda c: c.data == "change_channel" and c.from_user.id in ADMIN_IDS)
async def change_channel_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not CHANNEL_IDS:
        return await callback.answer("❌ هیچ کانالی در تنظیمات رندر تعریف نشده است!", show_alert=True)
        
    inline_keyboard = []
    for ch in CHANNEL_IDS:
        # نشانه گذاشتن برای کانالی که در حال حاضر انتخاب شده
        status = "✅ " if user_data.get(user_id, {}).get("target_channel") == ch else ""
        inline_keyboard.append([InlineKeyboardButton(text=f"{status}{ch}", callback_data=f"set_ch:{ch}")])
        
    inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_start")])
    kb = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    
    await callback.message.edit_text("🎯 کانال مورد نظر خودت رو برای ارسال پست انتخاب کن:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("set_ch:") and c.from_user.id in ADMIN_IDS)
async def set_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    selected_channel = callback.data.split(":", 1)[1]
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]["target_channel"] = selected_channel
    
    await callback.answer(f"کانال هدف به {selected_channel} تغییر یافت.")
    await callback.message.delete()
    await start(callback.message)

# ================== پروسه ساخت پست ==================
@dp.message()
async def handle_post(message: types.Message):
    user_id = message.from_user.id
    
    # 🔒 قفل اختصاصی ادمین‌ها
    if user_id not in ADMIN_IDS:
        await message.answer("❌ شما اجازه استفاده از این ربات را ندارید.")
        return

    # بررسی استپ برای دکمه شیشه‌ای جدید
    if user_data.get(user_id, {}).get("step") == "waiting_button":
        await save_button(message)
        return

    # اگر کاربر از قبل کانال انتخاب نکرده، پیش‌فرض ست بشه
    target_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)

    # شروع پروسه ساخت پست جدید با حفظ کانال انتخابی کاربر
    user_data[user_id] = {
        "message": message, 
        "buttons": [], 
        "layout": "single",
        "step": None,
        "target_channel": target_ch
    }
    await show_post_menu(message.chat.id, user_id)

async def show_post_menu(chat_id, user_id):
    data = user_data.get(user_id)
    btn_count = len(data["buttons"])
    layout_text = "تک ردیفه 🟦" if data["layout"] == "single" else "دو ردیفه 🟩"
    target_ch = data["target_channel"]
    
    text = (
        f"✅ **پست شما دریافت شد!**\n"
        f"🎯 ارسال خواهد شد به: <b>{target_ch}</b>\n"
        f"🔢 تعداد دکمه‌های شیشه‌ای: {btn_count} عدد\n"
        f"📐 چیدمان دکمه‌ها: **{layout_text}**\n\n"
        f"👇 گزینه‌ی مورد نظر رو انتخاب کن:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه شیشه‌ای", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="👁️ پیش‌نمایش پست", callback_data="preview_post")],
        [InlineKeyboardButton(text="📤 ارسال نهایی به کانال", callback_data="send_to_channel")]
    ])
    
    await bot.send_message(chat_id, text, reply_markup=kb)

@dp.callback_query(lambda c: c.data == "add_button" and c.from_user.id in ADMIN_IDS)
async def add_button_prompt(callback: types.CallbackQuery):
    user_data[callback.from_user.id]["step"] = "waiting_button"
    await callback.message.answer("📌 **فرمت:** `متن دکمه | لینک`\n💡 **مثال:** `گوگل | https://google.com`")
    await callback.answer()

async def save_button(message: types.Message):
    user_id = message.from_user.id
    try:
        text, url = [x.strip() for x in message.text.split("|", 1)]
        if not url.startswith("http"): url = "https://" + url
        user_data[user_id]["buttons"].append({"text": text, "url": url})
        user_data[user_id]["step"] = None
        await message.answer("✅ دکمه اضافه شد.")
        await show_post_menu(message.chat.id, user_id)
    except:
        await message.answer("❌ فرمت اشتباه! دوباره بفرست: `متن | لینک`")

@dp.callback_query(lambda c: c.data == "toggle_layout" and c.from_user.id in ADMIN_IDS)
async def toggle_layout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data[user_id]["layout"] = "double" if user_data[user_id]["layout"] == "single" else "single"
    await callback.answer("📐 چیدمان دکمه‌ها تغییر کرد.")
    await show_post_menu(callback.message.chat.id, user_id)

def build_keyboard(buttons, layout):
    if not buttons: return None
    inline_keyboard = []
    if layout == "single":
        for b in buttons: inline_keyboard.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
    else:
        row = []
        for b in buttons:
            row.append(InlineKeyboardButton(text=b["text"], url=b["url"]))
            if len(row) == 2:
                inline_keyboard.append(row)
                row = []
        if row: inline_keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

@dp.callback_query(lambda c: c.data == "preview_post" and c.from_user.id in ADMIN_IDS)
async def preview_post(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_data.get(user_id)
    await callback.message.answer("👇 👁️ **پیش‌نمایش پست شما:**")
    await forward_or_send(callback.message.chat.id, data["message"], build_keyboard(data["buttons"], data["layout"]))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "send_to_channel" and c.from_user.id in ADMIN_IDS)
async def send_to_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_data.get(user_id)
    target_ch = data["target_channel"]
    
    try:
        await forward_or_send(target_ch, data["message"], build_keyboard(data["buttons"], data["layout"]))
        await callback.answer(f"🚀 پست با موفقیت به کانال {target_ch} ارسال شد!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ خطا! مطمئن شوید ربات در کانال {target_ch} ادمین است.\nمشخصات: {str(e)}", show_alert=True)

async def forward_or_send(target_chat, original, keyboard):
    if original.text: await bot.send_message(target_chat, original.text, reply_markup=keyboard)
    elif original.photo: await bot.send_photo(target_chat, original.photo[-1].file_id, caption=original.caption, reply_markup=keyboard)
    elif original.video: await bot.send_video(target_chat, original.video.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.document: await bot.send_document(target_chat, original.document.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.voice: await bot.send_voice(target_chat, original.voice.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.audio: await bot.send_audio(target_chat, original.audio.file_id, caption=original.caption, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "back_to_start" and c.from_user.id in ADMIN_IDS)
async def back_to_start(callback: types.CallbackQuery):
    await callback.message.delete()
    user_data[callback.from_user.id]["step"] = None
    await start(callback.message)

# ================== Webhook Server ==================
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = types.Update.model_validate(json_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        if not webhook_url.endswith("/webhook"): webhook_url = webhook_url.rstrip("/") + "/webhook"
        await bot.set_webhook(webhook_url)
        print(f"🚀 Webhook set to: {webhook_url}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
