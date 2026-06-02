from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Request
import os

TOKEN = os.getenv("BOT_TOKEN")

# 👥 دریافت لیست ادمین‌ها از رندر
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
    return user_id in ADMIN_IDS manipulation

# تابع کمکی برای ریست کردن یا ساخت دیتای اولیه ادمین
def init_user_data(user_id: int, reset_channel: bool = False):
    prev_channel = user_data.get(user_id, {}).get("target_channel") if not reset_channel else None
    user_data[user_id] = {
        "message": None, 
        "edited_text": None, 
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

    init_user_data(user_id)
    current_channel = user_data[user_id]["target_channel"]

    text = (
        "👋 <b>سلام رئیس! به ربات دکمه‌ساز و مدیریت کانال خوش آمدی.</b>\n\n"
        f"📢 کانال فعلی شما برای ارسال پست: <b>{current_channel}</b>\n\n"
        "📝 <b>چطور کار می‌کند؟</b>\n"
        "کافیست متن، عکس، ویدیو، وویس یا فایل داکیومنت خود را به ربات بفرستید تا منوی ساخت دکمه و ویرایش برای شما باز شود.\n\n"
        "⚙️ برای تنظیمات یا ریستارت از پنل زیر استفاده کنید:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ پنل مدیریت و تنظیمات", callback_data="admin_panel")],
    ])
        
    await message.answer(text, reply_markup=kb)

# ================== 🔄 دستور اختصاصی /clear (پاکسازی حافظه) ==================
@dp.message(Command("clear"))
async def clear_memory_command(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id): return

    # پاکسازی کامل وضعیت و دکمه‌های در حال ساخت بدون تغییر کانال هدف
    init_user_data(user_id, reset_channel=False)
    
    text = (
        "🧹 <b>حافظه ربات با موفقیت پاکسازی شد!</b>\n\n"
        "🔄 وضعیت شما به حالت اولیه برگشت. دکمه‌ها یا متن‌های نیمه‌کاره حذف شدند.\n"
        "اکنون می‌توانید بدون مشکل پست جدید خود را بفرستید یا از دستور /start استفاده کنید."
    )
    await message.answer(text)

# ================== دستور /help ==================
@dp.message(Command("help"))
async def help_command(message: types.Message):
    if not is_admin(message.from_user.id): return
    text = (
        "🤖 <b>راهنمای سریع دستورات ربات:</b>\n\n"
        "🔹 /start - بازگشت به منوی اصلی و بازنشانی وضعیت\n"
        "🔹 /clear - 🧹 پاکسازی فوری حافظه ربات در صورت هنگ کردن دکمه‌ها\n"
        "🔹 /help - نمایش این منوی راهنما\n\n"
        "💡 <b>ارسال گروهی دکمه‌ها:</b> شما می‌توانید چندین دکمه را یکجا بفرستید! کافیست هر دکمه را در یک خط جدید با فرمت <code>متن | لینک</code> وارد کنید."
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

# 🔄 عملیات دکمه ریستارت
@dp.callback_query(lambda c: c.data == "restart_bot_data")
async def restart_bot_data(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return

    init_user_data(user_id, reset_channel=True)
    await callback.answer("🔄 ربات با موفقیت ریستارت شد و حافظه موقت شما پاک گردید.", show_alert=True)
    await callback.message.delete()
    await start(callback.message)

# ================== هسته پردازش پیام‌ها و استپ‌ها ==================
@dp.message()
async def handle_incoming_messages(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id): return

    # اگر پیام دستور تلگرامی بود (مثل /start یا /clear)، به عنوان پست جدید پردازش نشود
    if message.text and message.text.startswith("/"):
        return

    current_step = user_data.get(user_id, {}).get("step")

    # ۱. حالت دریافت دکمه شیشه‌ای (تکی یا گروهی)
    if current_step == "waiting_button":
        await save_multiple_buttons(message)
        return

    # ۲. حالت دریافت متن یا کپشن ویرایش شده
    if current_step == "waiting_edit_text":
        await save_edited_text(message)
        return

    # ۳. دریافت پیام جدید (متن، عکس، فیلم و...) برای ساخت پست از صفر
    current_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)
    user_data[user_id] = {
        "message": message, 
        "edited_text": None, 
        "buttons": [], 
        "layout": "single",
        "step": None,
        "target_channel": current_ch
    }
    await show_post_menu(message.chat.id, user_id)

# ================== منوی مدیریت دکمه‌ها، ویرایش و ارسال ==================
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
        "👇 دکمه‌های خود را اضافه کنید، متن را ویرایش کنید یا پست را ارسال کنید:"
    )
    
    keyboard_structure = [
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه (تکی یا گروهی)", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="✏️ ویرایش متن / کپشن پست", callback_data="edit_post_text")],
        [InlineKeyboardButton(text="👁️ پیش‌نمایش پست", callback_data="preview_post")],
        [InlineKeyboardButton(text="📤 ارسال نهایی پست به کانال", callback_data="send_final_action")],
        [InlineKeyboardButton(text="🔙 انصراف و بازگشت", callback_data="back_to_start")]
    ]
    
    await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_structure))

# --- بخش اضافه کردن هوشمند دکمه‌ها ---
@dp.callback_query(lambda c: c.data == "add_button")
async def add_button_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_button"
    
    instruction = (
        "📌 **فرمت ارسال دکمه (تکی یا گروهی):**\n"
        "<code>متن دکمه | لینک</code>\n\n"
        "💡 **نکته عالی:** می‌توانید چند دکمه را یکجا بفرستید! کافیست هر دکمه را در یک **خط جدید** بنویسید. مانند:\n"
        "<code>📥 دانلود فیلم | https://site.com/1</code>\n"
        "<code>💬 بخش نظرات | https://site.com/2</code>"
    )
    await callback.message.answer(instruction)
    await callback.answer()

async def save_multiple_buttons(message: types.Message):
    user_id = message.from_user.id
    
    if message.text and message.text.startswith("/"):
        user_data[user_id]["step"] = None
        return

    lines = message.text.strip().split("\n")
    success_count = 0
    
    for line in lines:
        if not line.strip() or "|" not in line:
            continue
        try:
            text, url = [x.strip() for x in line.split("|", 1)]
            if not url.startswith("http"): 
                url = "https://" + url
            user_data[user_id]["buttons"].append({"text": text, "url": url})
            success_count += 1
        except:
            continue
            
    if success_count > 0:
        user_data[user_id]["step"] = None
        await message.answer(f"✅ تعداد {success_count} دکمه با موفقیت به لیست اضافه شد.")
        await show_post_menu(message.chat.id, user_id)
    else:
        await message.answer("❌ هیچ دکمه سالمی یافت نشد! لطفاً فرمت را رعایت کنید:\n`متن | لینک` (هر دکمه در یک خط)")

# --- بخش ویرایش متن / کپشن ---
@dp.callback_query(lambda c: c.data == "edit_post_text")
async def edit_post_text_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_edit_text"
    await callback.message.answer("✏️ **حالا متن یا کپشن جدید خود را ارسال کنید:**\n(دکمه‌های شیشه‌ای قبلی شما بدون تغییر باقی می‌مانند)")
    await callback.answer()

async def save_edited_text(message: types.Message):
    user_id = message.from_user.id
    
    if message.text and message.text.startswith("/"):
        user_data[user_id]["step"] = None
        return

    user_data[user_id]["edited_text"] = message.text
    user_data[user_id]["step"] = None
    await message.answer("✅ متن جدید با موفقیت ذخیره شد.")
    await show_post_menu(message.chat.id, user_id)

# --- چیدمان دکمه‌ها ---
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
        await forward_or_send(callback.message.chat.id, data["message"], build_keyboard(data["buttons"], data["layout"]), data["edited_text"])
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
        await forward_or_send(target_ch, data["message"], keyboard, data["edited_text"])
        await callback.answer("🚀 پست با موفقیت به کانال ارسال شد!", show_alert=True)
        
        init_user_data(user_id)
        await callback.message.delete()
        await start(callback.message)
    except Exception as e:
        await callback.answer(f"❌ خطا! مطمئن شوید ربات در کانال ادمین است.\nمشخصات: {str(e)}", show_alert=True)

# تابع هوشمند ارسال با پشتیبانی از متن جایگزین
async def forward_or_send(target_chat, original, keyboard, edited_text=None):
    text_to_send = edited_text if edited_text else (original.text if original.text else original.caption)

    if original.text: 
        await bot.send_message(target_chat, text_to_send, reply_markup=keyboard)
    elif original.photo: 
        await bot.send_photo(target_chat, original.photo[-1].file_id, caption=text_to_send, reply_markup=keyboard)
    elif original.video: 
        await bot.send_video(target_chat, original.video.file_id, caption=text_to_send, reply_markup=keyboard)
    elif original.document: 
        await bot.send_document(target_chat, original.document.file_id, caption=text_to_send, reply_markup=keyboard)
    elif original.voice: 
        await bot.send_voice(target_chat, original.voice.file_id, caption=text_to_send, reply_markup=keyboard)
    elif original.audio: 
        await bot.send_audio(target_chat, original.audio.file_id, caption=text_to_send, reply_markup=keyboard)

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
    # ⭐ اضافه کردن منوی دستورات به تلگرام به محض روشن شدن ربات
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 منوی اصلی"),
        BotCommand(command="clear", description="🧹 پاکسازی حافظه و رفع هنگ"),
        BotCommand(command="help", description="❓ راهنمای ربات")
    ])

    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        if not webhook_url.endswith("/webhook"): webhook_url = webhook_url.rstrip("/") + "/webhook"
        await bot.set_webhook(webhook_url)
        print(f"🚀 Webhook set to: {webhook_url}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
