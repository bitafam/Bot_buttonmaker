from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Request
import os

TOKEN = os.getenv("BOT_TOKEN")

# 👥 لیست ادمین‌ها از رندر
ADMINS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_STR.split(",") if x.strip().isdigit()]

# 📢 لیست کانال‌ها از رندر
CHANNELS_STR = os.getenv("CHANNEL_IDS", "")
CHANNEL_IDS = [x.strip() for x in CHANNELS_STR.split(",") if x.strip()]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
app = FastAPI()

# 🗄️ دیتابیس موقت در حافظه سرور
user_data = {}

# 🔒 تابع بررسی ادمین با امنیت بالا
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ================== دستور /start ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("❌ شما دسترسی به این ربات شخصی را ندارید.")
        return

    # مقداردهی اولیه دیتای کاربر
    user_data[user_id] = {
        "buttons": [], 
        "layout": "single", 
        "step": None, 
        "target_channel": CHANNEL_IDS[0] if CHANNEL_IDS else None
    }

    current_channel = user_data[user_id]["target_channel"]

    text = (
        "👋 <b>سلام رئیس! به ربات دکمه‌ساز حرفه‌ای خوش آمدی.</b>\n\n"
        f"📢 کانال فعلی برای ارسال دکمه: <b>{current_channel}</b>\n\n"
        "📖 <b>راهنمای کار با ربات:</b>\n"
        "۱. ابتدا پست چندفایلی (آلبوم)، متن یا ویدیو خود را دستی در کانال قرار دهید.\n"
        "۲. سپس در این ربات با زدن دکمه <b>«➕ اضافه کردن دکمه شیشه‌ای»</b> دکمه‌های خود را بسازید.\n"
        "۳. در نهایت گزینه‌ی <b>«🚀 ارسال دکمه خالی به کانال»</b> را بزنید تا دکمه‌ها دقیقاً زیر پست قبلی شما در کانال بنشینند.\n\n"
        "ℹ️ برای دیدن لیست دستورات ربات دستور /help را ارسال کنید."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه شیشه‌ای", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="🔄 تغییر کانال هدف", callback_data="change_channel")],
        [InlineKeyboardButton(text="🚀 ارسال دکمه خالی به کانال", callback_data="send_pure_buttons")]
    ])
        
    await message.answer(text, reply_markup=kb)

# ================== دستور /help ==================
@dp.message(Command("help"))
async def help_command(message: types.Message):
    if not is_admin(message.from_user.id): return
    text = (
        "🤖 <b>لیست دستورات و کلیدهای ربات:</b>\n\n"
        "🔹 /start - راه‌اندازی مجدد ربات و نمایش منوی اصلی مدیریت دکمه‌ها\n"
        "🔹 /help - نمایش همین منوی راهنما\n\n"
        "💡 <b>نکته حرفه‌ای:</b> برای اینکه دکمه‌ها دقیقاً زیر آلبوم چندفایلی شما چسبیده دیده شوند، بلافاصله بعد از فرستادن پست در کانال، دکمه‌ها را از ربات ارسال کنید."
    )
    await message.answer(text)

# ================== بخش تغییر کانال ==================
@dp.callback_query(lambda c: c.data == "change_channel")
async def change_channel_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
        
    if not CHANNEL_IDS:
        return await callback.answer("❌ هیچ کانالی تعریف نشده است!", show_alert=True)
        
    inline_keyboard = []
    for ch in CHANNEL_IDS:
        status = "✅ " if user_data.get(user_id, {}).get("target_channel") == ch else ""
        inline_keyboard.append([InlineKeyboardButton(text=f"{status}{ch}", callback_data=f"set_ch:{ch}")])
        
    inline_keyboard.append([InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_to_start")])
    await callback.message.edit_text("🎯 کانال مورد نظر خود را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard))

@dp.callback_query(lambda c: c.data.startswith("set_ch:"))
async def set_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    
    selected_channel = callback.data.split(":", 1)[1]
    user_data[user_id]["target_channel"] = selected_channel
    
    await callback.answer(f"کانال هدف تغییر کرد.")
    await callback.message.delete()
    await start(callback.message)

# ================== پروسه مدیریت و دریافت دکمه‌ها ==================
@dp.message()
async def handle_buttons_input(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id): return

    # اگر کاربر در حال فرستادن متن دکمه است
    if user_data.get(user_id, {}).get("step") == "waiting_button":
        try:
            text, url = [x.strip() for x in message.text.split("|", 1)]
            if not url.startswith("http"): url = "https://" + url
            
            user_data[user_id]["buttons"].append({"text": text, "url": url})
            user_data[user_id]["step"] = None
            
            await message.answer(f"✅ دکمه <b>{text}</b> اضافه شد.")
            await show_current_status(message.chat.id, user_id)
        except:
            await message.answer("❌ فرمت اشتباه! لطفاً مجدداً به این صورت بفرستید:\n`متن دکمه | لینک`")

async def show_current_status(chat_id, user_id):
    data = user_data.get(user_id)
    btn_count = len(data["buttons"])
    layout_text = "تک ردیفه 🟦" if data["layout"] == "single" else "دو ردیفه 🟩"
    
    text = (
        f"📊 **وضعیت دکمه‌های ساخته شده:**\n"
        f"🎯 کانال هدف: <b>{data['target_channel']}</b>\n"
        f"🔢 تعداد دکمه‌ها تا این لحظه: {btn_count} عدد\n"
        f"📐 چیدمان دکمه‌ها: **{layout_text}**\n\n"
        "می‌توانید دکمه‌های بیشتری اضافه کنید یا چیدمان را تغییر دهید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه بیشتر", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="🚀 ارسال دکمه خالی به کانال", callback_data="send_pure_buttons")]
    ])
    await bot.send_message(chat_id, text, reply_markup=kb)

@dp.callback_query(lambda c: c.data == "add_button")
async def add_button_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_button"
    await callback.message.answer("📌 **فرمت ارسال دکمه:**\n`متن دکمه | لینک`\n\n💡 **مثال:**\n`📥 دانلود فایل | https://site.com/file`")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "toggle_layout")
async def toggle_layout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["layout"] = "double" if user_data[user_id]["layout"] == "single" else "single"
    await callback.answer("📐 چیدمان دکمه‌ها تغییر کرد.")
    await show_current_status(callback.message.chat.id, user_id)

# تابع ساخت دکمه‌ها
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

# ================== 🚀 ارسال دکمه خالص به کانال ==================
@dp.callback_query(lambda c: c.data == "send_pure_buttons")
async def send_pure_buttons(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    
    data = user_data.get(user_id)
    if not data["buttons"]:
        return await callback.answer("⚠️ ابتدا باید حداقل یک دکمه بسازید!", show_alert=True)
        
    target_ch = data["target_channel"]
    keyboard = build_keyboard(data["buttons"], data["layout"])
    
    try:
        # ترفند ارسال کاراکتر نامرئی به همراه دکمه شیشه‌ای برای چسبیده دیده شدن به پست قبلی
        invisible_char = "‎" 
        await bot.send_message(chat_id=target_ch, text=invisible_char, reply_markup=keyboard)
        
        # ریست کردن دکمه‌ها بعد از ارسال موفق
        user_data[user_id]["buttons"] = []
        
        await callback.answer("🚀 دکمه‌ها با موفقیت به صورت مستقل به کانال ارسال شدند!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ خطا! مطمئن شوید ربات در کانال ادمین است.\nمشخصات: {str(e)}", show_alert=True)

@dp.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.delete()
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
