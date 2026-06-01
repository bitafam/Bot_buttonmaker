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

# 🗄️ دیتابیس موقت در حافظه سرور
user_data = {}

# 🔒 تابع کمکی امنیتی برای تشخیص دقیق ادمین‌ها در تمام حالات
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ================== دستور /start ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ شما دسترسی به این ربات شخصی را ندارید.")
        return

    if user_id not in user_data:
        user_data[user_id] = {
            "message": None, 
            "buttons": [], 
            "layout": "single", 
            "step": None, 
            "target_channel": CHANNEL_IDS[0] if CHANNEL_IDS else None,
            "edit_message_id": None,
            "mode": "create" # می تواند create یا attach باشد
        }

    current_channel = user_data[user_id].get("target_channel")

    text = (
        "👋 <b>سلام رئیس! به ربات مدیریت کانال پیشرفته خوش آمدی.</b>\n\n"
        f"📢 کانال فعلی برای ارسال/ویرایش: <b>{current_channel}</b>\n\n"
        "🛠️ <b>ربات همزمان از دو روش پشتیبانی می‌کند:</b>\n"
        "۱. <b>ساخت پست جدید:</b> همین الان متن، عکس، فیلم یا فایل خود را بفرستید.\n"
        "۲. <b>اتصال دکمه به پست موجود:</b> پست مورد نظر را از کانال به اینجا <b>فوروارد</b> کنید.\n\n"
        "⚙️ برای تغییر کانال هدف از دکمه زیر استفاده کنید:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تغییر کانال هدف", callback_data="change_channel")]
    ])
        
    await message.answer(text, reply_markup=kb)

# ================== بخش تغییر کانال ==================
@dp.callback_query(lambda c: c.data == "change_channel")
async def change_channel_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        return await callback.answer("❌ عدم دسترسی", show_alert=True)
        
    if not CHANNEL_IDS:
        return await callback.answer("❌ هیچ کانالی تعریف نشده است!", show_alert=True)
        
    inline_keyboard = []
    for ch in CHANNEL_IDS:
        status = "✅ " if user_data.get(user_id, {}).get("target_channel") == ch else ""
        inline_keyboard.append([InlineKeyboardButton(text=f"{status}{ch}", callback_data=f"set_ch:{ch}")])
        
    inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_start")])
    await callback.message.edit_text("🎯 کانال مورد نظر خود را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))

@dp.callback_query(lambda c: c.data.startswith("set_ch:"))
async def set_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    
    selected_channel = callback.data.split(":", 1)[1]
    if user_id not in user_data: user_data[user_id] = {}
    user_data[user_id]["target_channel"] = selected_channel
    
    await callback.answer(f"کانال هدف به {selected_channel} تغییر یافت.")
    await callback.message.delete()
    await start(callback.message)

# ================== هسته اصلی پردازش پیام‌ها (هر دو روش) ==================
@dp.message()
async def handle_incoming_messages(message: types.Message):
    user_id = message.from_user.id
    
    # 🔒 بررسی دقیق ادمین بودن
    if not is_admin(user_id):
        await message.answer("❌ شما اجازه استفاده از این ربات را ندارید.")
        return

    # ۱. اگر منتظر دریافت دکمه شیشه‌ای جدید هستیم
    if user_data.get(user_id, {}).get("step") == "waiting_button":
        await save_button(message)
        return

    # ۲. هوشمندی ربات: تشخیص پیام فورواردی از کانال (روش دوم - اتصال دکمه)
    if message.forward_origin and hasattr(message.forward_origin, 'message_id'):
        msg_id = message.forward_origin.message_id
        target_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)

        user_data[user_id] = {
            "message": None,
            "buttons": [],
            "layout": "single",
            "step": None,
            "target_channel": target_ch,
            "edit_message_id": msg_id,
            "mode": "attach" # حالت اتصال دکمه به پست موجود
        }
        await show_post_menu(message.chat.id, user_id)
        return

    # ۳. دریافت پیام معمولی/مدیا برای ساخت پست جدید (روش اول - ساخت دستی)
    target_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)
    user_data[user_id] = {
        "message": message, 
        "buttons": [], 
        "layout": "single",
        "step": None,
        "target_channel": target_ch,
        "edit_message_id": None,
        "mode": "create" # حالت ساخت پست جدید
    }
    await show_post_menu(message.chat.id, user_id)

# ================== منوی مشترک مدیریت دکمه‌ها ==================
async def show_post_menu(chat_id, user_id):
    data = user_data.get(user_id)
    btn_count = len(data["buttons"])
    layout_text = "تک ردیفه 🟦" if data["layout"] == "single" else "دو ردیفه 🟩"
    target_ch = data["target_channel"]
    mode = data["mode"]
    
    if mode == "create":
        header_text = f"📝 <b>حالت: ساخت پست جدید دستی</b>\n🎯 ارسال به: <b>{target_ch}</b>"
        action_btn_text = "📤 ارسال نهایی به کانال"
        action_callback = "send_to_channel"
        extra_btns = [[InlineKeyboardButton(text="👁️ پیش‌نمایش پست", callback_data="preview_post")]]
    else:
        header_text = f"🔗 <b>حالت: اتصال دکمه به پست کانال</b>\n🎯 کانال هدف: <b>{target_ch}</b>\n🆔 آیدی پیام: <code>{data['edit_message_id']}</code>"
        action_btn_text = "🚀 اعمال دکمه‌ها روی پست کانال"
        action_callback = "apply_buttons_to_channel"
        extra_btns = []

    text = (
        f"{header_text}\n"
        f"🔢 تعداد دکمه‌های شیشه‌ای: {btn_count} عدد\n"
        f"📐 چیدمان دکمه‌ها: **{layout_text}**\n\n"
        f"👇 گزینه‌ی مورد نظر رو انتخاب کن:"
    )
    
    keyboard_structure = [
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه شیشه‌ای", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")]
    ]
    keyboard_structure.extend(extra_btns)
    keyboard_structure.append([InlineKeyboardButton(text=action_btn_text, callback_data=action_callback)])
    
    await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_structure))

@dp.callback_query(lambda c: c.data == "add_button")
async def add_button_prompt(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
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

# ================== اکشن‌های نهایی ارسال و ویرایش ==================
@dp.callback_query(lambda c: c.data == "preview_post")
async def preview_post(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    data = user_data.get(user_id)
    await callback.message.answer("👇 👁️ **پیش‌نمایش پست شما:**")
    await forward_or_send(callback.message.chat.id, data["message"], build_keyboard(data["buttons"], data["layout"]))
    await callback.answer()

@dp.callback_query(lambda c: c.data == "send_to_channel")
async def send_to_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    data = user_data.get(user_id)
    target_ch = data["target_channel"]
    
    try:
        await forward_or_send(target_ch, data["message"], build_keyboard(data["buttons"], data["layout"]))
        await callback.answer(f"🚀 پست با موفقیت به کانال {target_ch} ارسال شد!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ خطا در ارسال! مشخصات: {str(e)}", show_alert=True)

@dp.callback_query(lambda c: c.data == "apply_buttons_to_channel")
async def apply_buttons_to_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    data = user_data.get(user_id)
    target_ch = data["target_channel"]
    msg_id = data["edit_message_id"]
    keyboard = build_keyboard(data["buttons"], data["layout"])
    
    try:
        await bot.edit_message_reply_markup(chat_id=target_ch, message_id=msg_id, reply_markup=keyboard)
        await callback.answer("🔥 دکمه‌ها با موفقیت به پست کانال متصل شدند!", show_alert=True)
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
