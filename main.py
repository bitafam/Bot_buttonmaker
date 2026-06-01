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

# 🗄️ دیتابیس موقت در حافظه سرور برای مدیریت وضعیت هر ادمین
user_data = {}

# 🔒 تابع کمکی امنیتی برای تشخیص دقیق ادمین‌ها
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# تابع کمکی برای ریست کردن یا ساخت دیتای اولیه کاربر
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
        "👋 <b>سلام رئیس! به نسخه نهایی ربات مدیریت کانال خوش آمدی.</b>\n\n"
        f"📢 کانال فعلی شما برای عملیات: <b>{current_channel}</b>\n\n"
        "🛠️ <b>انتخاب روش کار با ربات:</b>\n"
        "۱. <b>ساخت پست دستی از صفر:</b> متن، عکس یا فایل خود را به ربات بفرستید.\n"
        "۲. <b>ارسال دکمه خالی (مستقل):</b> بدون فرستادن فایل، روی دکمه زیر بزنید و دکمه خالی برای زیر آلبوم بسازید.\n\n"
        "⚙️ برای مدیریت ربات، سوئیچ بین کانال‌ها یا ریستارت از پنل زیر استفاده کنید:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ساخت دکمه خالی (بدون فایل)", callback_data="start_pure_buttons")],
        [InlineKeyboardButton(text="⚙️ پنل مدیریت و تنظیمات", callback_data="admin_panel")],
    ])
        
    await message.answer(text, reply_markup=kb)

# ================== دستور /help ==================
@dp.message(Command("help"))
async def help_command(message: types.Message):
    if not is_admin(message.from_user.id): return
    text = (
        "🤖 <b>راهنمای سریع دستورات ربات:</b>\n\n"
        "🔹 /start - بازگشت به منوی اصلی و انتخاب روش کار\n"
        "🔹 /help - نمایش این منوی راهنما\n\n"
        "💡 <b>نکته برای پست‌های چند فایلی (آلبوم):</b> ابتدا پست را دستی در کانال بگذارید، سپس در ربات روی 'ساخت دکمه خالی' بزنید، دکمه‌ها را اضافه کنید و ارسال کنید تا دقیقاً زیر آلبوم شما چسبیده قرار بگیرد."
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
        "از منوی زیر برای تغییر کانال هدف یا ریستارت نرم‌افزاری ربات استفاده کنید:"
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

# ================== ورود به پروسه دکمه خالی ==================
@dp.callback_query(lambda c: c.data == "start_pure_buttons")
async def start_pure_buttons(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return

    user_data[user_id]["message"] = None  # یعنی این پست فایلی ندارد و فقط دکمه خالی است
    user_data[user_id]["buttons"] = []
    user_data[user_id]["layout"] = "single"
    user_data[user_id]["step"] = None

    await callback.message.delete()
    await show_post_menu(callback.message.chat.id, user_id)

# ================== هسته پردازش پیام‌ها (ساخت پست دستی) ==================
@dp.message()
async def handle_incoming_messages(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id): return

    # اگر کاربر در حال ارسال متن دکمه شیشه‌ای است
    if user_data.get(user_id, {}).get("step") == "waiting_button":
        await save_button(message)
        return

    # در غیر این صورت، پیام دریافتی (متن، عکس، فیلم) را به عنوان پست جدید دستی در نظر بگیر
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
    is_pure_button = data["message"] is None

    if is_pure_button:
        header_text = f"🟩 <b>حالت: ارسال دکمه خالی (بدون متن و فایل برای زیر آلبوم)</b>\n🎯 ارسال به: <b>{target_ch}</b>"
        action_btn_text = "🚀 ارسال دکمه خالی به کانال"
        action_callback = "send_final_action"
        extra_btns = []
    else:
        header_text = f"📝 <b>حالت: ساخت پست جدید دستی</b>\n🎯 ارسال به: <b>{target_ch}</b>"
        action_btn_text = "📤 ارسال نهایی پست به کانال"
        action_callback = "send_final_action"
        extra_btns = [[InlineKeyboardButton(text="👁️ پیش‌نمایش پست", callback_data="preview_post")]]

    text = (
        f"{header_text}\n"
        f"🔢 تعداد دکمه‌های شیشه‌ای: {btn_count} عدد\n"
        f"📐 چیدمان دکمه‌ها: **{layout_text}**\n\n"
        "👇 از گزینه‌های زیر برای تنظیم و ارسال نهایی استفاده کنید:"
    )
    
    keyboard_structure = [
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه شیشه‌ای", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")]
    ]
    keyboard_structure.extend(extra_btns)
    keyboard_structure.append([InlineKeyboardButton(text=action_btn_text, callback_data=action_callback)])
    keyboard_structure.append([InlineKeyboardButton(text="🔙 انصراف و بازگشت", callback_data="back_to_start")])
    
    await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_structure))

@dp.callback_query(lambda c: c.data == "add_button")
async def add_button_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_button"
    await callback.message.answer("📌 **فرمت ارسال دکمه:**\n`متن دکمه | لینک`\n\n💡 **مثال:**\n`📥 دانلود فایل | https://site.com/file`")
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
        await callback.message.answer("👇 👁️ **پیش‌نمایش پست دست‌ساز شما:**")
        await forward_or_send(callback.message.chat.id, data["message"], build_keyboard(data["buttons"], data["layout"]))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "send_final_action")
async def send_final_action(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    
    data = user_data.get(user_id)
    if not data["buttons"]:
        return await callback.answer("⚠️ ابتدا باید حداقل یک دکمه بسازید!", show_alert=True)
        
    target_ch = data["target_channel"]
    keyboard = build_keyboard(data["buttons"], data["layout"])
    
    try:
        if data["message"] is None:
            # 🚀 روش دوم: ارسال دکمه مستقل با کاراکتر نامرئی برای زیر آلبوم چندفایلی
            invisible_char = "‎" 
            await bot.send_message(chat_id=target_ch, text=invisible_char, reply_markup=keyboard)
            await callback.answer("🚀 دکمه خالی با موفقیت به کانال ارسال شد و زیر آلبوم جفت شد!", show_alert=True)
        else:
            # 📝 روش اول: ارسال پست دستی کامل ساخته شده در ربات
            await forward_or_send(target_ch, data["message"], keyboard)
            await callback.answer(f"🚀 پست کامل با موفقیت به کانال ارسال شد!", show_alert=True)
        
        # ریست کردن دکمه‌ها و اطلاعات پس از ارسال موفق
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
