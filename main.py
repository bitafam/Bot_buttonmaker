from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Request
import os

TOKEN = os.getenv("BOT_TOKEN")

# 👥 دریافت لیست ادمین‌ها از رندر و تبدیل به لیست عددی پایتون
ADMINS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_STR.split(",") if x.strip().isdigit()]

# 📢 دریافت لیست کانال‌ها از رندر
CHANNELS_STR = os.getenv("CHANNEL_IDS", "")
CHANNEL_IDS = [x.strip() for x in CHANNELS_STR.split(",") if x.strip()]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
app = FastAPI()

# 🗄️ دیتابیس موقت در حافظه سرور (کاملاً تفکیک‌شده برای هر کاربر)
user_data = {}

# 🔒 تابع امنیتی برای تشخیص دقیق ادمین‌ها
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# تابع کمکی برای ریست کردن یا ساخت دیتای اولیه ادمین
def init_user_data(user_id: int, reset_channel: bool = False):
    prev_channel = user_data.get(user_id, {}).get("target_channel") if not reset_channel else None
    user_data[user_id] = {
        "message": None, 
        "buttons": [], 
        "layout": "single", 
        "step": None, 
        "target_channel": prev_channel if prev_channel else (CHANNEL_IDS[0] if CHANNEL_IDS else None)
    }

# ================== دستور /start ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("❌ شما دسترسی به این ربات شخصی را ندارید.")
        return

    if user_id not in user_data:
        init_user_data(user_id)

    current_channel = user_data[user_id]["target_channel"]

    text = (
        "👋 <b>سلام رئیس! به ربات دکمه‌ساز و مدیریت کانال خوش آمدی.</b>\n\n"
        f"📢 کانال فعلی شما برای ارسال پست: <b>{current_channel}</b>\n\n"
        "📝 <b>چطور کار می‌کند؟</b>\n"
        "کافیست متن، عکس، ویدیو، وویس یا فایل داکیومنت خود را به ربات بفرستید. سپس ربات منوی ساخت دکمه شیشه‌ای را برای همان پست باز خواهد کرد.\n\n"
        "⚙️ برای مدیریت ربات، سوئیچ بین کانال‌ها یا ریستارت از پنل زیر استفاده کنید:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ پنل مدیریت و تنظیمات", callback_data="admin_panel")],
    ])
        
    await message.answer(text, reply_markup=kb)

# ================== دستور /help ==================
@dp.message(Command("help"))
async def help_command(message: types.Message):
    if not is_admin(message.from_user.id): return
    text = (
        "🤖 <b>راهنمای سریع دستورات ربات:</b>\n\n"
        "🔹 /start - بازگشت به منوی اصلی و بازنشانی وضعیت\n"
        "🔹 /help - نمایش این منوی راهنما\n\n"
        "💡 <b>نکته:</b> برای هر پست فقط یک پیام (متن یا فایل) بفرستید، دکمه‌ها را اضافه کنید و دکمه ارسال نهایی را بزنید."
    )
    await message.answer(text)

# ================== ⚙️ پنل مدیریت و تنظیمات پیشرفته ==================
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return

    text = (
        "⚙️ <b>پنل مدیریت و تنظیمات ربات</b>\n\n"
        f"👥 تعداد کل ادمین‌های مجاز: <code>{len(ADMIN_IDS)}</code> نفر\n"
        f"📢 تعداد کانال‌های متصل: <code>{len(CHANNEL_IDS)}</code> کانال\n"
        f"🎯 کانال فعال فعلی شما: <b>{user_data[user_id]['target_channel']}</b>\n\n"
        "از گزینه‌های زیر برای تغییر کانال یا ریستارت نرم‌افزاری ربات استفاده کنید:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تغییر کانال هدف", callback_data="change_channel")],
        [InlineKeyboardButton(text="🔄 ریستارت ربات و حافظه", callback_data="restart_bot_data")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_start")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data == "change_channel")
async def change_channel_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
        
    if not CHANNEL_IDS:
        return await callback.answer("❌ هیچ کانالی در رندر تعریف نشده است!", show_alert=True)
        
    inline_keyboard = []
    for ch in CHANNEL_IDS:
        status = "✅ " if user_data.get(user_id, {}).get("target_channel") == ch else ""
        inline_keyboard.append([InlineKeyboardButton(text=f"{status}{ch}", callback_data=f"set_ch:{ch}")])
        
    inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="admin_panel")])
    await callback.message.edit_text("🎯 کانال مورد نظر خود را برای ارسال انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))

@dp.callback_query(lambda c: c.data.startswith("set_ch:"))
async def set_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    
    selected_channel = callback.data.split(":", 1)[1]
    user_data[user_id]["target_channel"] = selected_channel
    
    await callback.answer(f"کانال هدف به {selected_channel} تغییر یافت.")
    await admin_panel(callback)

# 🔄 عملیات دکمه ریستارت (پاک کردن حافظه نشست کاربر در صورت بروز اختلال)
@dp.callback_query(lambda c: c.data == "restart_bot_data")
async def restart_bot_data(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return

    init_user_data(user_id, reset_channel=True)
    await callback.answer("🔄 ربات با موفقیت ریستارت شد و حافظه موقت شما پاک گردید.", show_alert=True)
    await callback.message.delete()
    await start(callback.message)

# ================== هسته پردازش پیام‌ها (ساخت پست دستی) ==================
@dp.message()
async def handle_incoming_messages(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id): return

    # ۱. اگر کاربر در حال ارسال متن دکمه شیشه‌ای است
    if user_data.get(user_id, {}).get("step") == "waiting_button":
        await save_button(message)
        return

    # ۲. دریافت پیام جدید (متن، عکس، فیلم و...) برای ساخت پست
    current_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)
    user_data[user_id] = {
        "message": message, 
        "buttons": [], 
        "layout": "single",
        "step": None,
        "target_channel": current_ch
    }
    await show_post_menu(message.chat.id, user_id)

# ================== منوی مدیریت دکمه‌ها و ارسال ==================
async def show_post_menu(chat_id, user_id):
    data = user_data.get(user_id)
    btn_count = len(data["buttons"])
    layout_text = "تک ردیفه 🟦" if data["layout"] == "single" else "دو ردیفه 🟩"
    target_ch = data["target_channel"]

    text = (
        f"📝 <b>حالت: ساخت پست جدید</b>\n"
        f"🎯 کانال هدف: <b>{target_ch}</b>\n"
        f"🔢 تعداد دکمه‌های شیشه‌ای: {btn_count} عدد\n"
        f"📐 چیدمان دکمه‌ها: **{layout_text}**\n\n"
        "👇 دکمه‌های خود را اضافه کنید یا پست را ارسال کنید:"
    )
    
    keyboard_structure = [
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه شیشه‌ای", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="👁️ پیش‌نمایش پست", callback_data="preview_post")],
        [InlineKeyboardButton(text="📤 ارسال نهایی پست به کانال", callback_data="send_final_action")],
        [InlineKeyboardButton(text="🔙 انصراف و بازگشت", callback_data="back_to_start")]
    ]
    
    await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_structure))

@dp.callback_query(lambda c: c.data == "add_button")
async def add_button_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_button"
    await callback.message.answer("📌 **فرمت ارسال دکمه:**\n<code>متن دکمه | لینک</code>\n\n💡 **مثال:**\n<code>📥 دانلود فایل | https://site.com/file</code>")
    await callback.answer()

async def save_button(message: types.Message):
    user_id = message.from_user.id
    try:
        text, url = [x.strip() for x in message.text.split("|", 1)]
        if not url.startswith("http"): url = "https://" + url
        user_data[user_id]["buttons"].append({"text": text, "url": url})
        user_data[user_id]["step"] = None
        await message.answer("✅ دکمه با موفقیت اضافه شد.")
        await show_post_menu(message.chat.id, user_id)
    except:
        await message.answer("❌ فرمت اشتباه! دوباره بفرستید:\n`متن | لینک`")

@dp.callback_query(lambda c: c.data == "toggle_layout")
async def toggle_layout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
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

# ================== عملیات نهایی ارسال و پیش‌نمایش ==================
@dp.callback_query(lambda c: c.data == "preview_post")
async def preview_post(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    data = user_data.get(user_id)
    if data["message"]:
        await callback.message.answer("👇 👁️ **پیش‌نمایش پست شما:**")
        await forward_or_send(callback.message.chat.id, data["message"], build_keyboard(data["buttons"], data["layout"]))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "send_final_action")
async def send_final_action(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    
    data = user_data.get(user_id)
    if not data["message"]:
        return await callback.answer("⚠️ پستی برای ارسال وجود ندارد. ابتدا یک فایل یا متن بفرستید.", show_alert=True)
        
    target_ch = data["target_channel"]
    keyboard = build_keyboard(data["buttons"], data["layout"])
    
    try:
        # ارسال پست کامل ساخته شده به همراه کیبورد دکمه‌ها
        await forward_or_send(target_ch, data["message"], keyboard)
        await callback.answer("🚀 پست با موفقیت به کانال ارسال شد!", show_alert=True)
        
        # پاکسازی حافظه موقت این ادمین و هدایت به منوی اول
        init_user_data(user_id)
        await callback.message.delete()
        await start(callback.message)
    except Exception as e:
        await callback.answer(f"❌ خطا! مطمئن شوید ربات در کانال ادمین است.\nمشخصات: {str(e)}", show_alert=True)

async def forward_or_send(target_chat, original, keyboard):
    if original.text: await bot.send_message(target_chat, original.text, reply_markup=keyboard)
    elif original.photo: await bot.send_photo(target_chat, original.photo[-1].file_id, caption=original.caption, reply_markup=keyboard)
    elif original.video: await bot.send_video(target_chat, original.video.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.document: await bot.send_document(target_chat, original.document.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.voice: await bot.send_voice(target_chat, original.voice.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.audio: await bot.send_audio(target_chat, original.audio.file_id, caption=original.caption, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.delete()
    init_user_data(callback.from_user.id)
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
