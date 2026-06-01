from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import FastAPI, Request
import os

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))  # آیدی عددی تلگرام خودت را در رندر ست کن

# تنظیم پارس‌مد روی HTML برای نسخه‌های جدید aiogram 3.x
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
app = FastAPI()

# دیتابیس موقت در حافظه سرور
user_data = {}

# ================== دستور /start ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    # 🔒 قفل اختصاصی ادمین
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ شما دسترسی به این ربات شخصی را ندارید.")
        return

    text = (
        "👋 سلام رئیس! به ربات پست‌ساز پیشرفته خودت خوش آمدی.\n\n"
        "📝 همین الان **متن یا رسانه (عکس، ویدیو، فایل)** خودت رو بفرست تا بریم برای ساخت پست."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ پنل مدیریت ربات", callback_data="admin_panel")]
    ])
        
    await message.answer(text, reply_markup=kb)

# ================== پنل مدیریت ==================
@dp.callback_query(lambda c: c.data == "admin_panel" and c.from_user.id == ADMIN_ID)
async def admin_panel(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_start")]
    ])
    await callback.message.edit_text(
        "📊 **پنل مدیریت ربات:**\n\n"
        "تنظیمات کانال شما برقرار است. ربات آماده دریافت پست‌های جدید شماست.", 
        reply_markup=kb
    )

# ================== پروسه ساخت پست ==================
@dp.message()
async def handle_post(message: types.Message):
    user_id = message.from_user.id
    
    # 🔒 قفل اختصاصی ادمین
    if user_id != ADMIN_ID:
        await message.answer("❌ شما اجازه استفاده از این ربات را ندارید.")
        return

    # بررسی اینکه آیا کاربر در حال فرستادن دکمه جدید است
    if user_data.get(user_id, {}).get("step") == "waiting_button":
        await save_button(message)
        return

    # شروع پروسه ساخت پست جدید و ذخیره فایل اصلی
    user_data[user_id] = {
        "message": message, 
        "buttons": [], 
        "layout": "single", # حالت پیش‌فرض: تک ردیفه
        "step": None
    }
    await show_post_menu(message.chat.id, user_id)

async def show_post_menu(chat_id, user_id):
    data = user_data.get(user_id)
    btn_count = len(data["buttons"])
    layout_text = "تک ردیفه 🟦" if data["layout"] == "single" else "دو ردیفه 🟩"
    
    text = (
        f"✅ **پست شما دریافت شد!**\n"
        f"🔢 تعداد دکمه‌های شیشه‌ای فعلی: {btn_count} عدد\n"
        f"📐 چیدمان فعلی دکمه‌ها: **{layout_text}**\n\n"
        f"👇 از منوی زیر برای تنظیم، پیش‌نمایش یا ارسال نهایی استفاده کنید:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه شیشه‌ای", callback_data="add_button")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="👁️ پیش‌نمایش پست", callback_data="preview_post")],
        [InlineKeyboardButton(text="📤 ارسال نهایی به کانال", callback_data="send_to_channel")]
    ])
    
    await bot.send_message(chat_id, text, reply_markup=kb)

# مرحله درخواست وارد کردن دکمه
@dp.callback_query(lambda c: c.data == "add_button" and c.from_user.id == ADMIN_ID)
async def add_button_prompt(callback: types.CallbackQuery):
    user_data[callback.from_user.id]["step"] = "waiting_button"
    await callback.message.answer(
        "📌 **فرمت ارسال دکمه:**\n"
        "`متن دکمه | لینک`\n\n"
        "💡 **مثال:**\n"
        "`گوگل | https://google.com`"
    )
    await callback.answer()

# ذخیره کردن دکمه فرستاده شده
async def save_button(message: types.Message):
    user_id = message.from_user.id
    try:
        text, url = [x.strip() for x in message.text.split("|", 1)]
        if not url.startswith("http"): 
            url = "https://" + url
            
        user_data[user_id]["buttons"].append({"text": text, "url": url})
        user_data[user_id]["step"] = None
        
        await message.answer("✅ دکمه با موفقیت اضافه شد.")
        await show_post_menu(message.chat.id, user_id)
    except:
        await message.answer("❌ فرمت اشتباه است! لطفاً دوباره با فرمت درست بفرستید:\n`متن | لینک`")

# تغییر وضعیت چیدمان دکمه‌ها (تک یا دو ردیفه)
@dp.callback_query(lambda c: c.data == "toggle_layout" and c.from_user.id == ADMIN_ID)
async def toggle_layout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current = user_data[user_id]["layout"]
    user_data[user_id]["layout"] = "double" if current == "single" else "single"
    await callback.answer("📐 چیدمان دکمه‌ها تغییر کرد.")
    await show_post_menu(callback.message.chat.id, user_id)

# تابع کمکی برای ساخت کیبورد براساس چیدمان انتخابی
def build_keyboard(buttons, layout):
    if not buttons: 
        return None
    
    inline_keyboard = []
    if layout == "single":
        # هر دکمه در یک ردیف جداگانه
        for b in buttons:
            inline_keyboard.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
    else:
        # دو دکمه در هر ردیف
        row = []
        for b in buttons:
            row.append(InlineKeyboardButton(text=b["text"], url=b["url"]))
            if len(row) == 2:
                inline_keyboard.append(row)
                row = []
        if row: # برای دکمه‌های فرد باقی‌مانده
            inline_keyboard.append(row)
            
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# پیش‌نمایش پست قبل از ارسال
@dp.callback_query(lambda c: c.data == "preview_post" and c.from_user.id == ADMIN_ID)
async def preview_post(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_data.get(user_id)
    
    original = data["message"]
    keyboard = build_keyboard(data["buttons"], data["layout"])
    
    await callback.message.answer("👇 👁️ **پیش‌نمایش پست شما در کانال:**")
    await forward_or_send(callback.message.chat.id, original, keyboard)
    await callback.answer()

# ارسال نهایی به کانال تلگرام
@dp.callback_query(lambda c: c.data == "send_to_channel" and c.from_user.id == ADMIN_ID)
async def send_to_channel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_data.get(user_id)
    
    if not data: 
        return await callback.answer("خطا! اطلاعات پست یافت نشد.", show_alert=True)
    
    original = data["message"]
    keyboard = build_keyboard(data["buttons"], data["layout"])
    
    try:
        await forward_or_send(CHANNEL_ID, original, keyboard)
        await callback.answer("🚀 پست با موفقیت به کانال ارسال شد!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ خطا در ارسال! مطمئن شوید ربات در کانال ادمین است.\nمشخصات خطا: {str(e)}", show_alert=True)

# تابع همگانی برای کپی کردن دقیق انواع پست (متن، عکس، ویدیو، صدا و...) همراه با کپشن و دکمه شیشه‌ای
async def forward_or_send(target_chat, original, keyboard):
    if original.text:
        await bot.send_message(target_chat, original.text, reply_markup=keyboard)
    elif original.photo:
        await bot.send_photo(target_chat, original.photo[-1].file_id, caption=original.caption, reply_markup=keyboard)
    elif original.video:
        await bot.send_video(target_chat, original.video.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.document:
        await bot.send_document(target_chat, original.document.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.voice:
        await bot.send_voice(target_chat, original.voice.file_id, caption=original.caption, reply_markup=keyboard)
    elif original.audio:
        await bot.send_audio(target_chat, original.audio.file_id, caption=original.caption, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "back_to_start" and c.from_user.id == ADMIN_ID)
async def back_to_start(callback: types.CallbackQuery):
    await callback.message.delete()
    user_data[callback.from_user.id] = {"step": None}
    await start(callback.message)

# ================== Webhook Server (FastAPI) ==================
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
        if not webhook_url.endswith("/webhook"):
            webhook_url = webhook_url.rstrip("/") + "/webhook"
        await bot.set_webhook(webhook_url)
        print(f"🚀 Webhook set to: {webhook_url}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
