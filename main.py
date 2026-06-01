from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Request
import os

TOKEN = os.getenv("BOT_TOKEN")

# 👥 لیست ادمین‌ها (جدا شده با ویرگول در رندر)
ADMINS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_STR.split(",") if x.strip().isdigit()]

# 📢 لیست کانال‌ها (جدا شده با ویرگول در رندر)
CHANNELS_STR = os.getenv("CHANNEL_IDS", "")
CHANNEL_IDS = [x.strip() for x in CHANNELS_STR.split(",") if x.strip()]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
app = FastAPI()

# 🗄️ دیتابیس موقت در حافظه
user_data = {}

# ================== دستور /start ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("❌ شما دسترسی به این ربات شخصی را ندارید.")
        return

    if user_id not in user_data:
        user_data[user_id] = {"buttons": [], "layout": "single", "step": None, "target_channel": None, "edit_message_id": None}

    if not user_data[user_id].get("target_channel") and CHANNEL_IDS:
        user_data[user_id]["target_channel"] = CHANNEL_IDS[0]

    current_channel = user_data[user_id]["target_channel"]

    text = (
        "👋 **سلام رئیس! به ربات دکمه‌ساز خوش آمدی.**\n\n"
        f"📢 کانال فعلی: <b>{current_channel}</b>\n\n"
        "👇 **چطوری کار میکنه؟**\n"
        "۱. ابتدا پست رو (هرجور که دوست داری؛ آلبوم، فایل، متن) دستی داخل کانالت منتشر کن.\n"
        "۲. سپس اون پست رو از کانال برای این ربات **فوروارد** کن.\n\n"
        "⚙️ برای جابجایی بین کانال‌ها از دکمه زیر استفاده کن:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تغییر کانال هدف", callback_data="change_channel")]
    ])
    await message.answer(text, reply_markup=kb)

# ================== تغییر کانال هدف ==================
@dp.callback_query(lambda c: c.data == "change_channel" and c.from_user.id in ADMIN_IDS)
async def change_channel_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not CHANNEL_IDS:
        return await callback.answer("❌ هیچ کانالی تعریف نشده است!", show_alert=True)
        
    inline_keyboard = []
    for ch in CHANNEL_IDS:
        status = "✅ " if user_data.get(user_id, {}).get("target_channel") == ch else ""
        inline_keyboard.append([InlineKeyboardButton(text=f"{status}{ch}", callback_data=f"set_ch:{ch}")])
        
    inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_start")])
    await callback.message.edit_text("🎯 کانال مورد نظر رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))

@dp.callback_query(lambda c: c.data.startswith("set_ch:") and c.from_user.id in ADMIN_IDS)
async def set_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    selected_channel = callback.data.split(":", 1)[1]
    user_data[user_id]["target_channel"] = selected_channel
    await callback.answer(f"کانال هدف تغییر کرد.")
    await callback.message.delete()
    await start(callback.message)

# ================== دریافت پیام فورواردی یا متن دکمه‌ها ==================
@dp.message()
async def handle_incoming_messages(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return

    # وضعیت: کاربر در حال ارسال دکمه است
    if user_data.get(user_id, {}).get("step") == "waiting_button":
        await save_button(message)
        return

    # وضعیت: کاربر یک پیام را از کانال فوروارد کرده است
    if message.forward_origin:
        # ذخیره آیدی پیام فوروارد شده برای ویرایش‌های بعدی
        msg_id = message.forward_from_message_id
        if not msg_id:
            await message.answer("❌ خطایی رخ داد. مطمئن شو پیام رو دقیقاً از خود کانال فوروارد کردی و مخفی‌سازی آیدی فرستنده نداری.")
            return

        target_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)

        # ریست کردن اطلاعات دکمه‌های قبلی برای پیام جدید
        user_data[user_id]["edit_message_id"] = msg_id
        user_data[user_id]["buttons"] = []
        user_data[user_id]["layout"] = "single"
        user_data[user_id]["step"] = None

        await show_button_menu(message.chat.id, user_id)
    else:
        await message.answer("⚠️ لطفاً ابتدا پست مورد نظر را از کانال به اینجا **فوروارد** کنید.")

async def show_button_menu(chat_id, user_id):
    data = user_data.get(user_id)
    btn_count = len(data["buttons"])
    layout_text = "تک ردیفه 🟦" if data["layout"] == "single" else "دو ردیفه 🟩"
    msg_id = data["edit_message_id"]
    target_ch = data["target_channel"]
    
    text = (
        f"📍 **پیام کانال شناسایی شد!**\n"
        f"🆔 آیدی پیام در کانال: `{msg_id}`\n"
        f"🎯 کانال هدف: <b>{target_ch}</b>\n"
        f"🔢 تعداد دکمه‌های فعلی: {btn_count} عدد\n"
        f"📐 چیدمان دکمه‌ها: **{layout_text}**\n\n"
        "حالا دکمه‌های خودت رو اضافه کن و در آخر روی اعمال دکمه‌ها بزن:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه شیشه‌ای", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="🚀 اعمال دکمه‌ها روی پست کانال", callback_data="apply_buttons_to_channel")]
    ])
    await bot.send_message(chat_id, text, reply_markup=kb)

@dp.callback_query(lambda c: c.data == "add_button" and c.from_user.id in ADMIN_IDS)
async def add_button_prompt(callback: types.CallbackQuery):
    user_data[callback.from_user.id]["step"] = "waiting_button"
    await callback.message.answer("📌 **فرمت:** `متن دکمه | لینک`\n💡 **مثال:** `دانلود فایل | https://site.com/file.zip`")
    await callback.answer()

async def save_button(message: types.Message):
    user_id = message.from_user.id
    try:
        text, url = [x.strip() for x in message.text.split("|", 1)]
        if not url.startswith("http"): url = "https://" + url
        user_data[user_id]["buttons"].append({"text": text, "url": url})
        user_data[user_id]["step"] = None
        await message.answer("✅ دکمه ذخیره شد.")
        await show_button_menu(message.chat.id, user_id)
    except:
        await message.answer("❌ فرمت اشتباه! دوباره بفرست: `متن | لینک`")

@dp.callback_query(lambda c: c.data == "toggle_layout" and c.from_user.id in ADMIN_IDS)
async def toggle_layout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data[user_id]["layout"] = "double" if user_data[user_id]["layout"] == "single" else "single"
    await callback.answer("📐 چیدمان تغییر کرد.")
    await show_button_menu(callback.message.chat.id, user_id)

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

# 🚀 عملیات اصلی: ویرایش کیبورد پست موجود در کانال
@dp.callback_query(lambda c: c.data == "apply_buttons_to_channel" and c.from_user.id in ADMIN_IDS)
async def apply_buttons_to_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_data.get(user_id)
    target_ch = data["target_channel"]
    msg_id = data["edit_message_id"]
    keyboard = build_keyboard(data["buttons"], data["layout"])
    
    try:
        # تلگرام با متد edit_message_reply_markup اجازه میده بدون تغییر متن یا عکس، فقط دکمه زیرش رو اضافه/ویرایش کنیم
        await bot.edit_message_reply_markup(chat_id=target_ch, message_id=msg_id, reply_markup=keyboard)
        await callback.answer("🔥 دکمه‌ها با موفقیت به پست کانال متصل شدند!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ خطا! مطمئن شوید ربات در کانال ادمین است و پیام خیلی قدیمی نیست.\nمشخصات: {str(e)}", show_alert=True)

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
