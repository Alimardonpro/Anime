import asyncio
import logging
import aiohttp
import json
import os
import re
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types, F, html
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from googletrans import Translator

# ==========================================
# ⚙️ KONFIGURATSIYA
# ==========================================
TOKEN = "8678636407:AAFdbKm91Ts-xU6dQyJ9udNwsBtTkLqufhc" 
CHANNEL_ID = "@AniZoneHD"
ADMIN_ID = 5064556873
VIDEO_BOT_USERNAME = "AniZoneHDbot"
BOT_USERNAME = "ZAnimeRobot"
DB_FILE = "anime_db.json"

dp = Dispatcher()
translator = Translator()
user_langs = {}

# ==========================================
# 💾 BAZA FUNKSIYALARI
# ==========================================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ==========================================
# 🧠 ADMIN FSM STATELARI
# ==========================================
class AdminUpload(StatesGroup):
    waiting_for_photo   = State()
    waiting_for_caption = State()
    waiting_for_custom_id = State()
    waiting_for_season_num = State()
    waiting_for_episodes   = State()
    waiting_for_movie_video = State()

# ==========================================
# 🛠 YORDAMCHI FUNKSIYALAR
# ==========================================
async def translate_title(text, dest_lang):
    if not text: return text
    try:
        res = await asyncio.to_thread(translator.translate, text, dest=dest_lang)
        return res.text
    except: return text

async def check_sub(bot: Bot, user_id: int) -> bool:
    if user_id == ADMIN_ID: return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except: return False

async def fetch_shikimori_info(query: str):
    headers = {"User-Agent": "ZAnimeRobot"}
    async with aiohttp.ClientSession() as session:
        url = f"https://shikimori.one/api/animes/{query}" if query.isdigit() else f"https://shikimori.one/api/animes?search={quote(query)}&limit=1"
        async with session.get(url, headers=headers) as r:
            if r.status == 200:
                data = await r.json()
                if isinstance(data, list) and data:
                    detail_url = f"https://shikimori.one/api/animes/{data[0]['id']}"
                    async with session.get(detail_url, headers=headers) as rd:
                        if rd.status == 200: return await rd.json()
                return data
    return None

# ==========================================
# ⌨️ TUGMALAR
# ==========================================
def get_lang_kb(args: str):
    arg_data = args if args else "none"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data=f"setlang_uz_{arg_data}"),
            InlineKeyboardButton(text="🇷🇺 Русский",   callback_data=f"setlang_ru_{arg_data}"),
            InlineKeyboardButton(text="🇯🇵 日本語",   callback_data=f"setlang_jp_{arg_data}")
        ]
    ])

def admin_menu_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📺 Serial qo'shish"),  KeyboardButton(text="🎬 Kino qo'shish")],
        [KeyboardButton(text="📚 Fasl qo'shish"),    KeyboardButton(text="📝 Oddiy post")],
        [KeyboardButton(text="📊 Baza holati"),       KeyboardButton(text="🏠 Asosiy menyu")]
    ], resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)

def finish_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Tayyor (Yopish)")]], resize_keyboard=True)

def get_seasons_kb(anime_id: str, db: dict):
    seasons = db.get(str(anime_id), {}).get("seasons", {})
    kb, row = [], []
    for s_num in sorted(seasons.keys(), key=lambda x: int(x)):
        row.append(InlineKeyboardButton(text=f"{s_num}-Fasl", callback_data=f"showeps_{anime_id}_{s_num}"))
        if len(row) == 2: kb.append(row); row = []
    if row: kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_episodes_kb(anime_id: str, season_num: str, db: dict):
    episodes = db.get(str(anime_id), {}).get("seasons", {}).get(str(season_num), {})
    kb, row = [], []
    for ep_num in sorted(episodes.keys(), key=lambda x: int(x)):
        row.append(InlineKeyboardButton(text=f"{ep_num}-qism", callback_data=f"play_{anime_id}_{season_num}_{ep_num}"))
        if len(row) == 3: kb.append(row); row = []
    if row: kb.append(row)
    kb.append([InlineKeyboardButton(text="🔙 Fasllarga qaytish", callback_data=f"backtoseasons_{anime_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==========================================
# 👑 ADMIN PANEL
# ==========================================
ADMIN_BUTTONS = {"📺 Serial qo'shish", "🎬 Kino qo'shish", "📚 Fasl qo'shish", "📝 Oddiy post", "📊 Baza holati", "🗑 Animeni o'chirish", "❌ Bekor qilish", "✅ Tayyor (Yopish)"}

@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👑 Admin Panelga xush kelibsiz!", reply_markup=admin_menu_kb())

@dp.message(F.text == "❌ Bekor qilish", F.from_user.id == ADMIN_ID)
async def cancel_upload(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Bekor qilindi.", reply_markup=admin_menu_kb())

@dp.message(F.text == "📊 Baza holati", F.from_user.id == ADMIN_ID)
async def db_status(message: Message):
    db = load_db()
    movies = sum(1 for v in db.values() if v.get("type") == "movie")
    series = sum(1 for v in db.values() if v.get("type") == "series")
    await message.answer(f"📦 <b>Baza holati:</b>\n🎬 Kinolar: <b>{movies}</b>\n📺 Seriallar: <b>{series}</b>\n📊 Jami: <b>{len(db)}</b> ta anime")

@dp.message(F.text.in_({"📺 Serial qo'shish", "🎬 Kino qo'shish", "📚 Fasl qo'shish", "📝 Oddiy post"}), F.from_user.id == ADMIN_ID)
async def step1_choose_type(message: Message, state: FSMContext):
    type_map = {"📺 Serial qo'shish": "serial", "🎬 Kino qo'shish": "movie", "📚 Fasl qo'shish": "season", "📝 Oddiy post": "post"}
    await state.update_data(post_type=type_map[message.text])
    await message.answer("📸 Rasm yuboring:", reply_markup=cancel_kb())
    await state.set_state(AdminUpload.waiting_for_photo)

@dp.message(AdminUpload.waiting_for_photo, F.photo, F.from_user.id == ADMIN_ID)
async def step2_get_photo(message: Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await message.answer("📝 Kanalga chiqadigan post matnini yuboring:")
    await state.set_state(AdminUpload.waiting_for_caption)

@dp.message(AdminUpload.waiting_for_caption, F.text, F.from_user.id == ADMIN_ID)
async def step3_get_caption(message: Message, state: FSMContext):
    await state.update_data(caption=message.text)
    data = await state.get_data()
    if data["post_type"] == "post":
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 Kanalimiz", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")]])
        await message.bot.send_photo(CHANNEL_ID, photo=data["photo_id"], caption=data["caption"], reply_markup=kb)
        await message.answer("🎉 Post kanalga chiqdi!", reply_markup=admin_menu_kb())
        await state.clear()
    else:
        await message.answer("🆔 Anime uchun O'Z ID sini kiriting (faqat raqam):")
        await state.set_state(AdminUpload.waiting_for_custom_id)

@dp.message(AdminUpload.waiting_for_custom_id, F.text, F.from_user.id == ADMIN_ID)
async def step4_get_custom_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit(): return await message.answer("⚠️ Faqat raqam kiriting!")
    custom_id = message.text.strip()
    db = load_db()
    if custom_id in db and (await state.get_data())["post_type"] != "season":
        return await message.answer(f"⚠️ Bu ID ({custom_id}) band! Boshqasini kiriting.")
    
    await state.update_data(anime_id=custom_id)
    data = await state.get_data()
    if data["post_type"] == "movie":
        await message.answer("🎬 Kino (video) faylini yuboring:")
        await state.set_state(AdminUpload.waiting_for_movie_video)
    else:
        await message.answer("📚 Nechanchi fasl?")
        await state.set_state(AdminUpload.waiting_for_season_num)

@dp.message(AdminUpload.waiting_for_movie_video, F.video | F.document, F.from_user.id == ADMIN_ID)
async def step5_movie_file(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id if message.video else message.document.file_id
    title_line = data["caption"].split("\n")[0] if data["caption"] else f"Anime {data['anime_id']}"
    
    db = load_db()
    db[str(data["anime_id"])] = {"type": "movie", "title": title_line, "video": file_id, "caption": data["caption"], "photo": data["photo_id"]}
    save_db(db)

    # YARATILGAN TUGMALAR (TOMOSHA QILISH VA ZANIMEROBOT)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Tomosha qilish", url=f"https://t.me/{VIDEO_BOT_USERNAME}?start=watch_{data['anime_id']}")],
        [InlineKeyboardButton(text="🔍 Anime haqida qiziqarli ma'lumot", url="https://t.me/ZAnimeRobot")]
    ])
    await message.bot.send_photo(CHANNEL_ID, photo=data["photo_id"], caption=data["caption"], reply_markup=kb)
    await message.answer("🎉 Kino yuklandi!", reply_markup=admin_menu_kb())
    await state.clear()

@dp.message(AdminUpload.waiting_for_season_num, F.text, F.from_user.id == ADMIN_ID)
async def step5_season_num(message: Message, state: FSMContext):
    if not message.text.strip().isdigit(): return await message.answer("⚠️ Faqat raqam kiriting.")
    await state.update_data(season=message.text.strip(), episodes={}, current_ep=1)
    await message.answer(f"✅ {message.text}-Fasl! Endi qismlarni yuboring. Tugagach '✅ Tayyor' ni bosing.", reply_markup=finish_kb())
    await state.set_state(AdminUpload.waiting_for_episodes)

@dp.message(AdminUpload.waiting_for_episodes, F.video | F.document, F.from_user.id == ADMIN_ID)
async def step6_receive_episode(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id if message.video else message.document.file_id
    data["episodes"][str(data["current_ep"])] = file_id
    await state.update_data(episodes=data["episodes"], current_ep=data["current_ep"] + 1)
    await message.answer(f"📥 {data['current_ep']}-qism qabul qilindi!")

@dp.message(AdminUpload.waiting_for_episodes, F.text == "✅ Tayyor (Yopish)", F.from_user.id == ADMIN_ID)
async def step7_finish_season(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data["episodes"]: return await message.answer("⚠️ Hali birorta ham qism yubormagansiz!")
    
    aid, s_num = str(data["anime_id"]), str(data["season"])
    title_line = data["caption"].split("\n")[0]
    
    db = load_db()
    if aid not in db: db[aid] = {"type": "series", "title": title_line, "seasons": {}}
    db[aid]["seasons"][s_num] = data["episodes"]
    db[aid]["caption"] = data["caption"]
    db[aid]["photo"] = data["photo_id"]
    save_db(db)

    # YARATILGAN TUGMALAR (TOMOSHA QILISH VA ZANIMEROBOT)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Tomosha qilish", url=f"https://t.me/{VIDEO_BOT_USERNAME}?start=watch_{aid}")],
        [InlineKeyboardButton(text="🔍 Anime haqida qiziqarli ma'lumot", url="https://t.me/ZAnimeRobot")]
    ])
    await message.bot.send_photo(CHANNEL_ID, photo=data["photo_id"], caption=data["caption"], reply_markup=kb)
    await message.answer("🎉 Fasl yuklandi!", reply_markup=admin_menu_kb())
    await state.clear()

# ==========================================
# 🎬 FOYDALANUVCHI QISMI
# ==========================================
async def send_anime_to_user(message: Message, anime_id: str, lang: str):
    clean_id = anime_id.replace("anime_", "").replace("watch_", "").strip()
    db = load_db()

    # --- 1. AGAR BAZADA BO'LSA ---
    if clean_id in db:
        anime = db[clean_id]
        
        # Boshqa tillarga ogohlantirish
        if lang != "uz":
            warn_msg = "😔 К сожалению, это аниме в нашей базе доступно только на Узбекском языке.\n✅ Вы можете посмотреть его на узбекском 👇" if lang == "ru" else "😔 ごめんなさい、このアニメはウズベク語でのみ利用可能です。\n✅ ウズベク語で見る 👇"
            await message.answer(warn_msg)
        
        caption_text = anime.get("caption", f"🎬 <b>{anime['title']}</b>")
        photo_id = anime.get("photo")
        
        # AQLLI QISM: Eski animelarda rasm bo'lmasa, Shikimori dan tortadi
        if not photo_id and clean_id.isdigit():
            info = await fetch_shikimori_info(clean_id)
            if info: 
                photo_id = f"https://shikimori.one{info.get('image', {}).get('original')}"
        
        # Mabodo rasm hech qayerdan topilmasa, Default anime rasmi turadi
        if not photo_id:
            photo_id = "https://telegra.ph/file/0c9cbfa943e86c5e25a2d.jpg"
            
        if anime["type"] == "movie":
            await message.answer_video(video=anime["video"], caption=f"{caption_text}\n\n🇺🇿 O'zbek tilida")
            return
            
        elif anime["type"] == "series":
            seasons = anime.get("seasons", {})
            kb_list = [[InlineKeyboardButton(text=f"{s_num}-Fasl", callback_data=f"showeps_{clean_id}_{s_num}")] for s_num in sorted(seasons.keys(), key=lambda x: int(x))]
            kb = InlineKeyboardMarkup(inline_keyboard=kb_list)
            
            try:
                await message.answer_photo(photo=photo_id, caption=f"{caption_text}\n\n👇 Faslni tanlang:", reply_markup=kb)
            except:
                await message.answer(f"{caption_text}\n\n👇 Faslni tanlang:", reply_markup=kb)
            return

    # --- 2. BAZADA BO'LMASA (SHIKIMORI DAN QIDIRAMIZ) ---
    status = await message.answer("🔎 Qidirilmoqda...")
    anime_info = await fetch_shikimori_info(clean_id)
    await status.delete()
    
    if anime_info:
        title_en = anime_info.get("name", "N/A")
        title_ru = anime_info.get("russian") or title_en
        image_url = f"https://shikimori.one{anime_info.get('image', {}).get('original')}"
        
        if lang == "uz":
            title_uz = await translate_title(title_ru, "uz")
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🇷🇺 Ruscha ko'rish (Animego)", url=f"https://animego.me/search/all?q={quote(title_ru)}")],
                [InlineKeyboardButton(text="📢 Kanalimiz", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")]
            ])
            caption = f"🎬 <b>{title_uz}</b>\n🇷🇺 {title_ru}\n━━━━━━━━━━━━━━━\n😔 O'zbekcha tarjimasi botda yo'q.\n✅ Lekin Ruscha ko'rishingiz mumkin 👇"
            
        elif lang == "ru":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🇷🇺 Смотреть на Animego", url=f"https://animego.me/search/all?q={quote(title_ru)}")],
                [InlineKeyboardButton(text="📢 Наш канал", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")]
            ])
            caption = f"🎬 <b>{title_ru}</b>\n━━━━━━━━━━━━━━━\n🔎 Аниме не найдено в базе.\n✅ Смотрите на сайтах 👇"

        else:
            title_jp = anime_info.get("japanese", [title_en])[0]
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🇯🇵 Shikimori", url=f"https://shikimori.one/animes/{anime_info['id']}")],
                [InlineKeyboardButton(text="📢 Kanalimiz", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")]
            ])
            caption = f"🎬 <b>{title_jp}</b>\n━━━━━━━━━━━━━━━\n🇯🇵 日本語で見る 👇"
            
        try: await message.answer_photo(photo=image_url, caption=caption, reply_markup=kb)
        except: await message.answer(caption, reply_markup=kb)
    else:
        await message.answer("❌ Anime topilmadi / Аниме не найдено.")

# ==========================================
# 🚀 HANDLERLAR
# ==========================================
@dp.message(CommandStart())
async def start_handler(message: Message, command: CommandObject, bot: Bot):
    user_id = message.from_user.id
    args = command.args or "none"

    if not await check_sub(bot, user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data=f"check_{args}")]
        ])
        return await message.answer("👋 Assalomu alaykum!\n\nBotdan foydalanish uchun avval kanalimizga obuna bo'ling 👇", reply_markup=kb)

    if args != "none" and (args.startswith("anime_") or args.startswith("watch_")):
        await message.answer("🌍 Qaysi tilda ko'rmoqchisiz? / Выберите язык:", reply_markup=get_lang_kb(args))
        return

    if user_id not in user_langs:
        await message.answer("🌍 Qaysi tilda anime ko'rmoqchisiz? / Выберите язык:", reply_markup=get_lang_kb("none"))
        return

    lang = user_langs[user_id]
    if lang == "uz": await message.answer("👋 Xush kelibsiz! Anime nomini yozing yoki ID bilan qidiring 🎬")
    elif lang == "ru": await message.answer("👋 Добро пожаловать! Напишите название аниме или ID 🎬")
    elif lang == "jp": await message.answer("👋 ようこそ！アニメの名前またはIDを入力してください 🎬")

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang_callback(call: CallbackQuery):
    parts = call.data.split("_", 2)
    lang, args = parts[1], parts[2]
    user_langs[call.from_user.id] = lang
    try: await call.message.delete()
    except: pass
    if args != "none":
        await send_anime_to_user(call.message, args, lang)
    else:
        if lang == "uz": await call.message.answer("✅ Til saqlandi! Anime nomini yoki ID yozing.")
        elif lang == "ru": await call.message.answer("✅ Язык сохранён! Напишите название или ID.")

@dp.callback_query(F.data.startswith("check_"))
async def check_sub_callback(call: CallbackQuery, bot: Bot):
    args = call.data.split("_", 1)[1]
    if await check_sub(bot, call.from_user.id):
        try: await call.message.delete()
        except: pass
        if args != "none":
            await call.message.answer("🌍 Tilni tanlang / Выберите язык:", reply_markup=get_lang_kb(args))
        else:
            await call.message.answer("🌍 Tilni tanlang / Выберите язык:", reply_markup=get_lang_kb("none"))
    else:
        await call.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True)

@dp.message(F.text & ~F.text.startswith("/"))
async def search_by_text(message: Message, bot: Bot):
    if message.from_user.id == ADMIN_ID and message.text in ADMIN_BUTTONS: return
    if not await check_sub(bot, message.from_user.id): return await message.answer("Botdan foydalanish uchun /start ni bosing.")
    
    lang = user_langs.get(message.from_user.id, "uz")
    db = load_db()
    query_lower = message.text.lower()
    found_in_db = message.text.strip() if message.text.strip().isdigit() and message.text.strip() in db else None
    
    if not found_in_db:
        for db_id, anime_data in db.items():
            if query_lower in anime_data.get("title", "").lower():
                found_in_db = db_id
                break

    await send_anime_to_user(message, found_in_db or message.text.strip(), lang)

# --- CALLBACKLAR ---
@dp.callback_query(F.data.startswith("showeps_"))
async def show_eps(call: CallbackQuery):
    _, aid, snum = call.data.split("_")
    db = load_db()
    
    eps = db.get(aid, {}).get("seasons", {}).get(snum, {})
    kb_list = []
    row = []
    
    for enum in sorted(eps.keys(), key=lambda x: int(x)):
        row.append(InlineKeyboardButton(text=f"{enum}-qism", callback_data=f"play_{aid}_{snum}_{enum}"))
        if len(row) == 3: 
            kb_list.append(row)
            row = []
    if row: 
        kb_list.append(row)
        
    kb_list.append([InlineKeyboardButton(text="🔙 Fasllarga qaytish", callback_data=f"backtoseasons_{aid}")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_list)
    
    matn = f"🎬 {snum}-Fasl qismlari 👇"
    
    try:
        await call.message.edit_caption(caption=matn, reply_markup=kb)
    except:
        try:
            await call.message.edit_text(text=matn, reply_markup=kb)
        except:
            pass
    await call.answer()

@dp.callback_query(F.data.startswith("backtoseasons_"))
async def back_to_seasons(call: CallbackQuery):
    aid = call.data.split("_")[1]
    db = load_db()
    
    anime = db.get(aid, {})
    caption_text = anime.get("caption", f"🎬 <b>{anime.get('title')}</b>")
    photo_id = anime.get("photo")
    
    # Orqaga qaytganda ham eskilar uchun aqlli rasm
    if not photo_id and aid.isdigit():
        info = await fetch_shikimori_info(aid)
        if info: photo_id = f"https://shikimori.one{info.get('image', {}).get('original')}"
        
    if not photo_id:
        photo_id = "https://telegra.ph/file/0c9cbfa943e86c5e25a2d.jpg"
    
    try:
        await call.message.delete()
        await call.message.answer_photo(photo=photo_id, caption=f"{caption_text}\n\n👇 Faslni tanlang:", reply_markup=get_seasons_kb(aid, db))
    except:
        await call.message.edit_text(f"{caption_text}\n\n👇 Faslni tanlang:", reply_markup=get_seasons_kb(aid, db))
        
    await call.answer()

@dp.callback_query(F.data.startswith("play_"))
async def play_video(call: CallbackQuery):
    _, aid, snum, enum = call.data.split("_")
    db = load_db()
    try:
        file_id = db[aid]["seasons"][snum][enum]
        title = db[aid].get('title')
        caption = f"🎬 <b>{title}</b>\n━━━━━━━━━━━━━━━\n📚 {snum}-Fasl  |  📺 {enum}-qism"
        await call.message.answer_video(video=file_id, caption=caption)
    except: await call.answer("⚠️ Video bazada topilmadi!", show_alert=True)

# ==========================================
# 🚀 MAIN
# ==========================================
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 @AniZoneHDbot (Video Bot) ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())