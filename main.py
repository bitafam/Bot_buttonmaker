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

# 🗄️ دیتابیس موقت در حافظه سرور
user_data = {}
channel_persistent_buttons = {}

# 🔒 تابع امنیتی برای تشخیص دقیق ادمین‌ها
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# تابع کمکی برای ریست کردن یا ساخت دیتای اولیه ادمین
def init_user_data(user_id: int, reset_channel: bool = False):
    prev_channel = user_data.get(user_id, {}).get("target_channel") if not reset_channel else None
    user_data[user_id] = {
        "message": None, 
        "edited_text": None, 
        "edited_entities": None, 
        "buttons": [], 
        "layout": "single", 
        "step": None, 
        "same_name_title": None,
        "target_channel": prev_channel if prev_channel else (CHANNEL_IDS[0] if CHANNEL_IDS else None)
    }

# ================== دستورات اصلی ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("❌ شما دسترسی به این ربات شخصی را ندارید.")
        return

    init_user_data(user_id)
    current_channel = user_data[user_id]["target_channel"]

    text = (
        "👋 <b>سلام رئیس! به ربات دکمه‌ساز فوق پیشرفته خوش آمدی.</b>\n\n"
        f"📢 کانال فعلی شما برای ارسال پست: <b>{current_channel}</b>\n\n"
        "⚙️ برای تنظیمات دکمه‌های ثابت کانال‌ها یا ریستارت از پنل زیر استفاده کنید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚙️ پنل مدیریت و تنظیمات پیشرفته", callback_data="admin_panel")]])
    await message.answer(text, reply_markup=kb)

@dp.message(Command("clear"))
async def clear_memory_command(message: types.Message):
    if not is_admin(message.from_user.id): return
    init_user_data(message.from_user.id, reset_channel=False)
    await message.answer("🧹 <b>حافظه موقت پست جاری با موفقیت پاکسازی و ریست شد!</b>")

# ================== ⚙️ پنل مدیریت و تنظیمات پیشرفته ==================
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return

    target_ch = user_data[user_id]['target_channel']
    p_btn = channel_persistent_buttons.get(target_ch)
    p_btn_status = f"✅ فعال ({p_btn['text']})" if p_btn else "❌ غیرفعال"

    text = (
        "⚙️ <b>پنل مدیریت و تنظیمات ربات</b>\n\n"
        f"🎯 کانال فعال فعلی: <b>{target_ch}</b>\n"
        f"🔗 دکمه ثابت این کانال: <b>{p_btn_status}</b>\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تغییر کانال هدف", callback_data="change_channel")],
        [InlineKeyboardButton(text="💎 تنظیم دکمه ثابت این کانال", callback_data="setup_persistent_btn")],
        [InlineKeyboardButton(text="🔄 ریستارت کل ربات و حافظه", callback_data="restart_bot_data")],
        [InlineKeyboardButton(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_start")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data == "change_channel")
async def change_channel_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
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

@dp.callback_query(lambda c: c.data == "restart_bot_data")
async def restart_bot_data(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    init_user_data(user_id, reset_channel=True)
    await callback.answer("🔄 ربات کاملاً ریستارت شد.", show_alert=True)
    await callback.message.delete()
    await start(callback.message)

@dp.callback_query(lambda c: c.data == "setup_persistent_btn")
async def setup_persistent_btn(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    target_ch = user_data[user_id]['target_channel']
    user_data[user_id]["step"] = "waiting_persistent_btn"
    await callback.message.answer(f"💎 <b>تنظیم دکمه ثابت برای کانال: {target_ch}</b>\n\nفرمت ارسال:\n<code>متن دکمه | لینک</code>\n\nبرای حذف عبارت <code>حذف</code> را بفرستید.")
    await callback.answer()

# ================== هسته پردازش پیام‌ها و استپ‌ها ==================
@dp.message()
async def handle_incoming_messages(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id): return
    if message.text and message.text.startswith("/"): return

    current_step = user_data.get(user_id, {}).get("step")

    if current_step == "waiting_persistent_btn":
        await save_persistent_button(message)
        return

    if current_step == "waiting_button":
        await save_multiple_buttons(message)
        return

    if current_step == "waiting_same_name_title":
        user_data[user_id]["same_name_title"] = message.text.strip()
        user_data[user_id]["step"] = "waiting_same_name_links"
        await message.answer(f"✅ اسم دکمه‌ها ثبت شد: <b>{message.text}</b>\n\n🔗 حالا لینک‌ها را خط به خط ارسال کنید:")
        return

    if current_step == "waiting_same_name_links":
        await save_same_name_buttons(message)
        return

    if current_step == "waiting_extract_links":
        await extract_links_from_post(message)
        return

    if current_step == "waiting_edit_text":
        user_data[user_id]["edited_text"] = message.text if message.text else message.caption
        user_data[user_id]["edited_entities"] = message.entities if message.entities else message.caption_entities
        user_data[user_id]["step"] = None
        await message.answer("✅ متن جدید با حفظ کامل استایل و فرمت ذخیره شد.")
        await show_post_menu(message.chat.id, user_id)
        return

    current_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)
    user_data[user_id] = {
        "message": message, 
        "edited_text": None, 
        "edited_entities": None,
        "buttons": [], 
        "layout": "single",
        "step": None,
        "same_name_title": None,
        "target_channel": current_ch
    }
    await show_post_menu(message.chat.id, user_id)

# ================== منوی مدیریت پست ==================
async def show_post_menu(chat_id, user_id):
    data = user_data.get(user_id)
    btn_count = len(data["buttons"])
    layout_text = "تک ردیفه 🟦" if data["layout"] == "single" else "دو ردیفه 🟩"

    text = (
        f"📝 <b>حالت: ساخت پست جدید</b>\n"
        f"🎯 کانال هدف: <b>{data['target_channel']}</b>\n"
        f"🔢 دکمه‌های فعلی شما: {btn_count} عدد\n"
        f"📐 چیدمان دکمه‌ها: <b>{layout_text}</b>\n\n"
        "👇 گزینه‌های مدیریت دکمه‌ها و ارسال:"
    )
    keyboard_structure = [
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه (متن | لینک)", callback_data="add_button")],
        [InlineKeyboardButton(text="🔗 دکمه‌های هم‌نام (فقط ارسال لینک)", callback_data="add_same_name_btn")],
        [InlineKeyboardButton(text="📥 استخراج لینک از پست فورواردی", callback_data="extract_links_btn")],
        [InlineKeyboardButton(text="✏️ ویرایش متنی دکمه‌های قبلی", callback_data="edit_existing_buttons")],
        [InlineKeyboardButton(text="🗑️ ریست و پاک کردن دکمه‌ها", callback_data="reset_buttons")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان دکمه‌ها", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="✏️ ویرایش متن / کپشن پست", callback_data="edit_post_text")],
        [InlineKeyboardButton(text="👁️ پیش‌نمایش پست", callback_data="preview_post")],
        [InlineKeyboardButton(text="🚀 ارسال نهایی به کانال", callback_data="send_final_action")],
        [InlineKeyboardButton(text="🔙 انصراف و بازگشت", callback_data="back_to_start")]
    ]
    await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_structure))

# --- پردازش ذخیره دکمه ثابت (پشتیبانی از tg:// اضافه شد) ---
async def save_persistent_button(message: types.Message):
    user_id = message.from_user.id
    target_ch = user_data[user_id]['target_channel']
    if message.text.strip() == "حذف":
        if target_ch in channel_persistent_buttons: del channel_persistent_buttons[target_ch]
        user_data[user_id]["step"] = None
        await message.answer(f"✅ دکمه ثابت کانال {target_ch} حذف شد.")
        return
    if "|" not in message.text:
        await message.answer("❌ فرمت اشتباه است. `متن | لینک` را رعایت کنید.")
        return
    try:
        text, url = [x.strip() for x in message.text.split("|", 1)]
        if not (url.startswith("http") or url.startswith("tg://")): url = "https://" + url
        channel_persistent_buttons[target_ch] = {"text": text, "url": url}
        user_data[user_id]["step"] = None
        await message.answer(f"✅ دکمه ثابت کانال {target_ch} تنظیم شد.")
    except: await message.answer("❌ خطا رخ داد.")

# --- افزودن دکمه معمولی (پشتیبانی از tg:// اضافه شد) ---
@dp.callback_query(lambda c: c.data == "add_button")
async def add_button_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_button"
    await callback.message.answer("📌 فرمت دکمه‌ها را بفرستید:\n<code>متن دکمه | لینک</code>")
    await callback.answer()

async def save_multiple_buttons(message: types.Message):
    user_id = message.from_user.id
    lines = message.text.strip().split("\n")
    success_count = 0
    for line in lines:
        if not line.strip() or "|" not in line: continue
        try:
            text, url = [x.strip() for x in line.split("|", 1)]
            if not (url.startswith("http") or url.startswith("tg://")): url = "https://" + url
            user_data[user_id]["buttons"].append({"text": text, "url": url})
            success_count += 1
        except: continue
    if success_count > 0:
        user_data[user_id]["step"] = None
        await message.answer(f"✅ تعداد {success_count} دکمه اضافه شد.")
        await show_post_menu(message.chat.id, user_id)
    else: await message.answer("❌ فرمت رعایت نشده است.")

# --- دکمه‌های هم‌نام (پشتیبانی از tg:// اضافه شد) ---
@dp.callback_query(lambda c: c.data == "add_same_name_btn")
async def add_same_name_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_same_name_title"
    await callback.message.answer("✍️ <b>اسم ثابت دکمه‌ها را وارد کنید:</b>")
    await callback.answer()

async def save_same_name_buttons(message: types.Message):
    user_id = message.from_user.id
    title = user_data[user_id]["same_name_title"]
    lines = message.text.strip().split("\n")
    success_count = 0
    for line in lines:
        url = line.strip()
        if not url: continue
        if not (url.startswith("http") or url.startswith("tg://")): url = "https://" + url
        user_data[user_id]["buttons"].append({"text": title, "url": url})
        success_count += 1
    if success_count > 0:
        user_data[user_id]["step"] = None
        user_data[user_id]["same_name_title"] = None
        await message.answer(f"✅ تعداد {success_count} دکمه هم‌نام ساخته شد.")
        await show_post_menu(message.chat.id, user_id)
    else: await message.answer("❌ لینکی یافت نشد.")

# --- قابلیت استخراج هوشمند لینک از پست فورواردی ---
@dp.callback_query(lambda c: c.data == "extract_links_btn")
async def extract_links_btn_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_extract_links"
    await callback.message.answer("📥 **حالا پست مورد نظر را به اینجا فوروارد کنید یا متن حاوی لینک را بفرستید:**")
    await callback.answer()

async def extract_links_from_post(message: types.Message):
    user_id = message.from_user.id
    extracted_buttons = []

    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url:
                    extracted_buttons.append({"text": btn.text, "url": btn.url})

    text = message.text if message.text else message.caption
    entities = message.entities if message.entities else message.caption_entities
    
    if text and entities:
        for ent in entities:
            if ent.type == "text_link":
                btn_text = text[ent.offset : ent.offset + ent.length]
                extracted_buttons.append({"text": btn_text, "url": ent.url})
            elif ent.type == "url":
                raw_url = text[ent.offset : ent.offset + ent.length]
                extracted_buttons.append({"text": "🔗 لینک منبع", "url": raw_url})

    if extracted_buttons:
        user_data[user_id]["buttons"].extend(extracted_buttons)
        user_data[user_id]["step"] = None
        await message.answer(f"✅ موفقیت‌آمیز! تعداد {len(extracted_buttons)} دکمه استخراج و اضافه شد.")
        await show_post_menu(message.chat.id, user_id)
    else:
        await message.answer("❌ هیچ لینکی پیدا نشد!")

# --- قابلیت ویرایش متنی دکمه‌های قبلی ---
@dp.callback_query(lambda c: c.data == "edit_existing_buttons")
async def edit_existing_buttons(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    buttons = user_data[user_id]["buttons"]
    if not buttons:
        return await callback.answer("⚠️ شما هنوز هیچ دکمه‌ای اضافه نکرده‌اید!", show_alert=True)
    lines = [f"{b['text']} | {b['url']}" for b in buttons]
    format_text = "\n".join(lines)
    user_data[user_id]["buttons"] = []
    user_data[user_id]["step"] = "waiting_button"
    
    output_message = (
        "✏️ <b>دکمه‌های قبلی شما ریست شدند و در کادر زیر قرار گرفتند.</b>\n\n"
        "کافیست کادر زیر را کپی کرده، تغییرات خود را اعمال کنید و همینجا ارسال کنید:\n\n"
        f"<code>{format_text}</code>"
    )
    await callback.message.answer(output_message)
    await callback.answer()

# --- سایر واکشی‌ها و توابع ابزار نظیر کیبورد، پیش‌نمایش و ارسال ---
@dp.callback_query(lambda c: c.data == "reset_buttons")
async def reset_buttons(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["buttons"] = []
    await callback.answer("🗑️ دکمه‌های این پست ریست شدند.", show_alert=True)
    await show_post_menu(callback.message.chat.id, user_id)

@dp.callback_query(lambda c: c.data == "edit_post_text")
async def edit_post_text_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_edit_text"
    await callback.message.answer("✏️ **حالا متن یا کپشن جدید خود را ارسال کنید:**")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "toggle_layout")
async def toggle_layout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["layout"] = "double" if user_data[user_id]["layout"] == "single" else "single"
    await callback.answer("📐 چیدمان دکمه‌ها تغییر کرد.")
    await show_post_menu(callback.message.chat.id, user_id)

def build_keyboard(buttons, layout, target_channel):
    all_buttons = list(buttons)
    p_btn = channel_persistent_buttons.get(target_channel)
    if p_btn: all_buttons.append({"text": p_btn["text"], "url": p_btn["url"]})
    if not all_buttons: return None
    inline_keyboard = []
    if layout == "single":
        for b in all_buttons: inline_keyboard.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
    else:
        row = []
        for b in all_buttons:
            if p_btn and b["url"] == p_btn["url"] and b["text"] == p_btn["text"]:
                if row: inline_keyboard.append(row); row = []
                inline_keyboard.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
                continue
            row.append(InlineKeyboardButton(text=b["text"], url=b["url"]))
            if len(row) == 2: inline_keyboard.append(row); row = []
        if row: inline_keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

@dp.callback_query(lambda c: c.data == "preview_post")
async def preview_post(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    data = user_data.get(user_id)
    if data["message"]:
        await callback.message.answer("👇 👁️ **پیش‌نمایش پست شما:**")
        kb = build_keyboard(data["buttons"], data["layout"], data["target_channel"])
        await forward_or_send(callback.message.chat.id, data["message"], kb, data["edited_text"], data["edited_entities"])
    await callback.answer()

@dp.callback_query(lambda c: c.data == "send_final_action")
async def send_final_action(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    data = user_data.get(user_id)
    if not data["message"]: return await callback.answer("⚠️ پستی وجود ندارد.", show_alert=True)
    target_ch = data["target_channel"]
    kb = build_keyboard(data["buttons"], data["layout"], target_ch)
    try:
        await forward_or_send(target_ch, data["message"], kb, data["edited_text"], data["edited_entities"])
        await callback.answer("🚀 پست با موفقیت ارسال شد!", show_alert=True)
        init_user_data(user_id)
        await callback.message.delete()
        await start(callback.message)
    except Exception as e: await callback.answer(f"❌ خطا! مشخصات: {str(e)}", show_alert=True)

async def forward_or_send(target_chat, original, keyboard, edited_text=None, edited_entities=None):
    text_to_send = edited_text if edited_text is not None else (original.text if original.text else original.caption)
    entities_to_send = edited_entities if edited_text is not None else (original.entities if original.text else original.caption_entities)

    if original.text: 
        await bot.send_message(target_chat, text_to_send, entities=entities_to_send, reply_markup=keyboard)
    elif original.photo: 
        await bot.send_photo(target_chat, original.photo[-1].file_id, caption=text_to_send, caption_entities=entities_to_send, reply_markup=keyboard)
    elif original.video: 
        await bot.send_video(target_chat, original.video.file_id, caption=text_to_send, caption_entities=entities_to_send, reply_markup=keyboard)
    elif original.document: 
        await bot.send_document(target_chat, original.document.file_id, caption=text_to_send, caption_entities=entities_to_send, reply_markup=keyboard)
    elif original.voice: 
        await bot.send_voice(target_chat, original.voice.file_id, caption=text_to_send, caption_entities=entities_to_send, reply_markup=keyboard)
    elif original.audio: 
        await bot.send_audio(target_chat, original.audio.file_id, caption=text_to_send, caption_entities=entities_to_send, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.delete(); init_user_data(callback.from_user.id); await start(callback.message)

# ================== Webhook Server ==================
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = types.Update.model_validate(json_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 منوی اصلی"),
        BotCommand(command="clear", description="🧹 پاکسازی حافظه پست جاری")
    ])
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        if not webhook_url.endswith("/webhook"): webhook_url = webhook_url.rstrip("/") + "/webhook"
        await bot.set_webhook(webhook_url)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
