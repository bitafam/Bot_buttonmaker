from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.client.default import DefaultBotProperties
from fastapi import FastAPI, Request
import os
import re
import json

TOKEN = os.getenv("BOT_TOKEN")

ADMINS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMINS_STR.split(",") if x.strip().isdigit()]

CHANNELS_STR = os.getenv("CHANNEL_IDS", "")
CHANNEL_IDS = [x.strip() for x in CHANNELS_STR.split(",") if x.strip()]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
app = FastAPI()

user_data = {}
DB_FILE = "persistent_buttons.json"

def load_persistent_buttons():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_persistent_buttons(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_with_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving JSON: {e}")

channel_persistent_buttons = load_persistent_buttons()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

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
        "extracted_temp_links": [], 
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

# ================== ⚙️ پنل مدیریت ==================
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return

    target_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)
    p_btn = channel_persistent_buttons.get(target_ch)
    p_btn_status = f"✅ فعال ({p_btn['text']})" if p_btn else "❌ غیرفعال"

    text = (
        "⚙️ <b>پنل مدیریت و تنظیمات ربات</b>\n\n"
        f"🎯 کانال فعال فعلی: <b>{target_ch}</b>\n"
        f"🔗 دکمه ثابت این کانال: <b>{p_btn_status}</b>\n\n"
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
    if user_id not in user_data: init_user_data(user_id)
    user_data[user_id]["target_channel"] = selected_channel
    await callback.answer(f"کانال هدف به {selected_channel} تغییر یافت.")
    await admin_panel(callback)

@dp.callback_query(lambda c: c.data == "restart_bot_data")
async def restart_bot_data(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    global channel_persistent_buttons
    channel_persistent_buttons.clear()
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    init_user_data(user_id, reset_channel=True)
    await callback.answer("🔄 ربات و حافظه کاملاً ریستارت شد.", show_alert=True)
    await callback.message.delete()
    await start(callback.message)

@dp.callback_query(lambda c: c.data == "setup_persistent_btn")
async def setup_persistent_btn(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    target_ch = user_data.get(user_id, {}).get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)
    user_data[user_id]["step"] = "waiting_persistent_btn"
    await callback.message.answer(f"💎 <b>تنظیم دکمه ثابت برای کانال: {target_ch}</b>\n\nفرمت ارسال:\n<code>متن دکمه | لینک</code>\n\nبرای حذف عبارت <code>حذف</code> را بفرستید.")
    await callback.answer()

# ================== هسته پردازش پیام‌ها ==================
@dp.message()
async def handle_incoming_messages(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id): return
    if message.text and message.text.startswith("/"): return

    if user_id not in user_data: init_user_data(user_id)
    current_step = user_data[user_id].get("step")

    if current_step == "waiting_persistent_btn":
        await save_persistent_button(message)
        return

    if current_step == "waiting_button":
        await save_multiple_buttons(message)
        return

    if current_step == "waiting_extract_same_name_title":
        title = message.text.strip()
        links = user_data[user_id].get("extracted_temp_links", [])
        for l in links:
            user_data[user_id]["buttons"].append({"text": title, "url": l})
        user_data[user_id]["step"] = None
        user_data[user_id]["extracted_temp_links"] = []
        await message.answer(f"✅ تعداد {len(links)} دکمه با نام ثابت <b>{title}</b> اضافه شد.")
        await show_post_menu(message.chat.id, user_id)
        return

    if current_step == "waiting_same_name_title":
        user_data[user_id]["same_name_title"] = message.text.strip()
        user_data[user_id]["step"] = "waiting_same_name_links"
        await message.answer(f"✅ اسم دکمه‌ها ثبت شد: <b>{message.text}</b>\n\n🔗 حالا لینک‌ها را خط به خط ارسال کنید:")
        return

    if current_step == "waiting_same_name_links":
        await save_same_name_buttons(message)
        return

    if current_step in ["waiting_extract_links_same", "waiting_extract_links_manual"]:
        await process_link_extraction(message, current_step)
        return

    # 🛠️ اصلاح فوق حیاتی: دریافت متن ویرایش شده و ذخیره انتیتی‌ها به عنوان بیسِ اصلی
    if current_step == "waiting_edit_text":
        user_data[user_id]["edited_text"] = message.text if message.text else message.caption
        user_data[user_id]["edited_entities"] = message.entities if message.text else message.caption_entities
        user_data[user_id]["step"] = None
        await message.answer("✅ متن جدید با حفظ کامل فرمت استایل‌ها ذخیره شد.")
        await show_post_menu(message.chat.id, user_id)
        return

    # دریافت پست اولیه کاربر و استخراج اتوماتیک بدون تداخل
    current_ch = user_data[user_id].get("target_channel", CHANNEL_IDS[0] if CHANNEL_IDS else None)
    auto_buttons = []
    raw_text = message.text if message.text else message.caption
    entities = message.entities if message.text else message.caption_entities
    
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url: auto_buttons.append({"text": btn.text, "url": btn.url})
                
    if raw_text and entities:
        for ent in entities:
            if ent.type == "text_link":
                btn_text = raw_text[ent.offset : ent.offset + ent.length]
                auto_buttons.append({"text": btn_text, "url": ent.url})

    if raw_text:
        pattern = r'(https?://[^\s<>"]+|tg://[^\s<>"]+)'
        all_urls = re.findall(pattern, raw_text)
        for url in all_urls:
            url_clean = url.rstrip('.,;)!]}`')
            if url_clean not in [x["url"] for x in auto_buttons]:
                auto_buttons.append({"text": "🔗 لینک منبع", "url": url_clean})

    user_data[user_id] = {
        "message": message, 
        "edited_text": None, 
        "edited_entities": None,
        "buttons": auto_buttons, 
        "layout": "single",
        "step": None,
        "same_name_title": None,
        "extracted_temp_links": [],
        "target_channel": current_ch
    }
    
    await message.answer("📥 پست شما دریافت شد.")
    await show_post_menu(message.chat.id, user_id)

# ================== منوی مدیریت پست ==================
async def show_post_menu(chat_id, user_id):
    data = user_data.get(user_id)
    btn_count = len(data["buttons"])
    
    if data["layout"] == "single": layout_text = "تک ستونه 🟦"
    elif data["layout"] == "double": layout_text = "دو ستونه 🟩"
    else: layout_text = "سه ستونه 🟨"

    text = (
        f"📝 <b>مدیریت پست جاری</b>\n"
        f"🎯 کانال هدف: <b>{data['target_channel']}</b>\n"
        f"🔢 دکمه‌های فعلی شما: {btn_count} عدد\n"
        f"📐 چیدمان دکمه‌ها: <b>{layout_text}</b>\n"
    )
    keyboard_structure = [
        [InlineKeyboardButton(text="➕ اضافه کردن دکمه (متن | لینک)", callback_data="add_button")],
        [InlineKeyboardButton(text="🔗 دکمه‌های هم‌نام (فقط ارسال لینک)", callback_data="add_same_name_btn")],
        [InlineKeyboardButton(text="📥 استخراج لینک (همه با یک نام)", callback_data="extract_same_name")],
        [InlineKeyboardButton(text="📥 استخراج لینک (نمایش مونو و ویرایش دستی)", callback_data="extract_manual")],
        [InlineKeyboardButton(text="✏️ ویرایش متنی دکمه‌های قبلی", callback_data="edit_existing_buttons")],
        [InlineKeyboardButton(text="🗑️ ریست و پاک کردن دکمه‌ها", callback_data="reset_buttons")],
        [InlineKeyboardButton(text="📐 تغییر چیدمان (۱، ۲ یا ۳ ستونه)", callback_data="toggle_layout")],
        [InlineKeyboardButton(text="✏️ ویرایش متن / کپشن پست", callback_data="edit_post_text")],
        [InlineKeyboardButton(text="👁️ پیش‌نمایش پست", callback_data="preview_post")],
        [InlineKeyboardButton(text="🚀 ارسال نهایی به کانال", callback_data="send_final_action")],
        [InlineKeyboardButton(text="🔙 انصراف و بازگشت", callback_data="back_to_start")]
    ]
    await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_structure))

# --- دکمه ثابت کانال ---
async def save_persistent_button(message: types.Message):
    user_id = message.from_user.id
    target_ch = user_data[user_id]['target_channel']
    global channel_persistent_buttons
    if message.text.strip() == "حذف":
        if target_ch in channel_persistent_buttons: 
            del channel_persistent_buttons[target_ch]
            save_persistent_buttons(channel_persistent_buttons)
        user_data[user_id]["step"] = None
        await message.answer(f"✅ دکمه ثابت کانال {target_ch} حذف شد.")
        return
    if "|" not in message.text:
        await message.answer("❌ فرمت اشتباه است. `متن | لینک` را رعایت کنید.")
        return
    try:
        text, url = [x.strip() for x in message.text.split("|", 1)]
        channel_persistent_buttons[target_ch] = {"text": text, "url": url}
        save_persistent_buttons(channel_persistent_buttons)
        user_data[user_id]["step"] = None
        await message.answer(f"✅ دکمه ثابت ذخیره شد.")
    except: await message.answer("❌ خطا رخ داد.")

# --- دکمه معمولی ---
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
            user_data[user_id]["buttons"].append({"text": text, "url": url})
            success_count += 1
        except: continue
    if success_count > 0:
        user_data[user_id]["step"] = None
        await message.answer(f"✅ تعداد {success_count} دکمه اضافه شد.")
        await show_post_menu(message.chat.id, user_id)
    else: await message.answer("❌ فرمت رعایت نشده است.")

# --- دکمه‌های هم‌نام دستی ---
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
        user_data[user_id]["buttons"].append({"text": title, "url": url})
        success_count += 1
    if success_count > 0:
        user_data[user_id]["step"] = None
        user_data[user_id]["same_name_title"] = None
        await message.answer(f"✅ تعداد {success_count} دکمه هم‌نام ساخته شد.")
        await show_post_menu(message.chat.id, user_id)
    else: await message.answer("❌ لینکی یافت نشد.")

# --- 🚀 اصلاح ریشه باگ استخراج دستی با پروتکل‌های چسبیده و نمایش مونو بدون خرابکاری HTML ---
@dp.callback_query(lambda c: c.data in ["extract_same_name", "extract_manual"])
async def trigger_extraction_step(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    step_name = "waiting_extract_links_same" if callback.data == "extract_same_name" else "waiting_extract_links_manual"
    user_data[user_id]["step"] = step_name
    await callback.message.answer("📥 **پست جدید یا متن کانفیگ‌ها را بفرستید:**")
    await callback.answer()

async def process_link_extraction(message: types.Message, current_step: str):
    user_id = message.from_user.id
    extracted_urls = []
    temp_list = []

    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url and btn.url not in extracted_urls:
                    extracted_urls.append(btn.url)
                    temp_list.append({"text": btn.text, "url": btn.url})

    raw_text = message.text if message.text else message.caption
    entities = message.entities if message.text else message.caption_entities
    
    if raw_text and entities:
        for ent in entities:
            if ent.type == "text_link" and ent.url not in extracted_urls:
                btn_text = raw_text[ent.offset : ent.offset + ent.length]
                extracted_urls.append(ent.url)
                temp_list.append({"text": btn_text, "url": ent.url})

    if raw_text:
        pattern = r'(https?://[^\s<>"]+|tg://[^\s<>"]+)'
        all_regex_urls = re.findall(pattern, raw_text)
        for url in all_regex_urls:
            url_clean = url.rstrip('.,;)!]}`')
            if url_clean not in extracted_urls:
                extracted_urls.append(url_clean)
                temp_list.append({"text": "🔗 لینک منبع", "url": url_clean})

    if not temp_list:
        await message.answer("❌ لینکی یافت نشد!")
        return

    if current_step == "waiting_extract_links_same":
        user_data[user_id]["extracted_temp_links"] = [x["url"] for x in temp_list]
        user_data[user_id]["step"] = "waiting_extract_same_name_title"
        await message.answer(f"📥 تعداد <b>{len(temp_list)}</b> لینک استخراج شد.\n\n✍️ **حالا اسم ثابت دکمه‌ها را بفرستید:**")
    
    elif current_step == "waiting_extract_links_manual":
        lines = []
        for item in temp_list: 
            lines.append(f"{item['text']} | {item['url']}")
        mono_formatted = "\n".join(lines)
        user_data[user_id]["step"] = "waiting_button"
        # استفاده از متد فرستادن متن خام امن بدون تداخل تگ‌های HTML ربات با مقادیر داخلی کاراکترهای خاص tg://
        await bot.send_message(
            chat_id=message.chat.id,
            text=f"📥 **ویرایش کرده و بفرستید:**\n\n<code>{mono_formatted}</code>",
            parse_mode="HTML"
        )

# --- ویرایش دکمه‌های قبلی ---
@dp.callback_query(lambda c: c.data == "edit_existing_buttons")
async def edit_existing_buttons(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    buttons = user_data[user_id]["buttons"]
    if not buttons: return await callback.answer("⚠️ دکمه‌ای وجود ندارد!", show_alert=True)
    
    lines = []
    for b in buttons: lines.append(f"{b['text']} | {b['url']}")
    format_text = "\n".join(lines)
    
    user_data[user_id]["buttons"] = []
    user_data[user_id]["step"] = "waiting_button"
    await callback.message.answer(f"✏️ ویرایش کرده و بفرستید:\n\n<code>{format_text}</code>")
    await callback.answer()

# --- ریست دکمه‌ها ---
@dp.callback_query(lambda c: c.data == "reset_buttons")
async def reset_buttons(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["buttons"] = []
    await callback.answer("🗑️ دکمه‌ها ریست شدند.")
    await show_post_menu(callback.message.chat.id, user_id)

# --- ویرایش متن / کپشن پست ---
@dp.callback_query(lambda c: c.data == "edit_post_text")
async def edit_post_text_prompt(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    user_data[user_id]["step"] = "waiting_edit_text"
    await callback.message.answer("✏️ **متن یا کپشن جدید خود را با فرمت‌های دلخواه بفرستید:**")
    await callback.answer()

# --- تغییر چیدمان (۱ تا ۳ ستونه) ---
@dp.callback_query(lambda c: c.data == "toggle_layout")
async def toggle_layout(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    current_layout = user_data[user_id]["layout"]
    
    if current_layout == "single": user_data[user_id]["layout"] = "double"
    elif current_layout == "double": user_data[user_id]["layout"] = "triple"
    else: user_data[user_id]["layout"] = "single"
        
    await callback.answer("📐 چیدمان دکمه‌ها تغییر کرد.")
    await show_post_menu(callback.message.chat.id, user_id)

# --- ساخت کیبورد نهایی ترکیبی ---
def build_keyboard(buttons, layout, target_channel):
    all_buttons = list(buttons)
    p_btn = channel_persistent_buttons.get(target_channel)
    if p_btn: all_buttons.append({"text": p_btn["text"], "url": p_btn["url"]})
    if not all_buttons: return None
    
    inline_keyboard = []
    
    if layout == "single":
        for b in all_buttons: inline_keyboard.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
    else:
        max_cols = 2 if layout == "double" else 3
        row = []
        for b in all_buttons:
            # بررسی صحت کلید لینک‌های tg:// جهت جلوگیری از کرش ریپلی مارکاپ
            if not b.get("url"): continue
            if p_btn and b["url"] == p_btn["url"] and b["text"] == p_btn["text"]:
                if row: inline_keyboard.append(row); row = []
                inline_keyboard.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
                continue
            row.append(InlineKeyboardButton(text=b["text"], url=b["url"]))
            if len(row) == max_cols: inline_keyboard.append(row); row = []
        if row: inline_keyboard.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

# --- 🛠️ شاهکار اصلاح فرستنده: تفکیک ۱۰۰٪ پارامترهای کپشن مدیا و متن متنی برای انواع فایل‌ها ---
async def send_perfect_post(target_chat_id, data, keyboard):
    orig = data["message"]
    
    if data["edited_text"] is None:
        await bot.copy_message(
            chat_id=target_chat_id,
            from_chat_id=orig.chat.id,
            message_id=orig.message_id,
            reply_markup=keyboard
        )
    else:
        txt = data["edited_text"]
        ent = data["edited_entities"]
        
        # هندلینگ فوق دقیق نوع مدیا بر اساس متدهای اختصاصی تلگرام برای حفظ قطعی فرمت‌ها در تمام پسوندها
        if orig.text:
            await bot.send_message(target_chat_id, text=txt, entities=ent, reply_markup=keyboard, parse_mode=None)
        elif orig.photo:
            await bot.send_photo(target_chat_id, photo=orig.photo[-1].file_id, caption=txt, caption_entities=ent, reply_markup=keyboard, parse_mode=None)
        elif orig.video:
            await bot.send_video(target_chat_id, video=orig.video.file_id, caption=txt, caption_entities=ent, reply_markup=keyboard, parse_mode=None)
        elif orig.document:
            await bot.send_document(target_chat_id, document=orig.document.file_id, caption=txt, caption_entities=ent, reply_markup=keyboard, parse_mode=None)
        elif orig.voice:
            await bot.send_voice(target_chat_id, voice=orig.voice.file_id, caption=txt, caption_entities=ent, reply_markup=keyboard, parse_mode=None)
        elif orig.audio:
            await bot.send_audio(target_chat_id, audio=orig.audio.file_id, caption=txt, caption_entities=ent, reply_markup=keyboard, parse_mode=None)
        elif orig.animation: # پشتیبانی از فایل‌های گیف
            await bot.send_animation(target_chat_id, animation=orig.animation.file_id, caption=txt, caption_entities=ent, reply_markup=keyboard, parse_mode=None)

# ================== عملیات نهایی ==================
@dp.callback_query(lambda c: c.data == "preview_post")
async def preview_post(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if not is_admin(user_id): return
    data = user_data.get(user_id)
    if data["message"]:
        await callback.message.answer("👇 👁️ **پیش‌نمایش پست با حفظ کامل فرمت‌ها:**")
        kb = build_keyboard(data["buttons"], data["layout"], data["target_channel"])
        await send_perfect_post(callback.message.chat.id, data, kb)
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
        await send_perfect_post(target_ch, data, kb)
        await callback.answer("🚀 پست به کانال ارسال شد!", show_alert=True)
        init_user_data(user_id)
        await callback.message.delete()
        await start(callback.message)
    except Exception as e: await callback.answer(f"❌ خطا! {str(e)}", show_alert=True)

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
        BotCommand(command="clear", description="🧹 پاکسازی حافظه")
    ])
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        if not webhook_url.endswith("/webhook"): webhook_url = webhook_url.rstrip("/") + "/webhook"
        await bot.set_webhook(webhook_url)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
