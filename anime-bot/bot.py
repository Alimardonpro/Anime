import asyncio
import logging
import aiohttp
import re
import json
import os
from urllib.parse import quote
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, URLInputFile
)
from googletrans import Translator

# ⚙️ KONFIGURATSIYA
TOKEN = "8702522776:AAF1en-NImh9wMwtPWFXFiQg9oHySiXqth0" 
CHANNEL_ID = "@AniZoneHD"
BOT_USERNAME = "ZAnimeRobot" 
VIDEO_BOT_USERNAME = "AniZoneHDbot" 
POSTED_LINKS_FILE = "posted_links.json"
ADMIN_ID = 5064556873 
admin_states = {}
news_posting_enabled = True  

dp = Dispatcher()
translator = Translator()
user_langs = {}
search_waiting = set()
order_waiting = set()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 💾 POSTED LINKS ---
def load_posted_links() -> set:
    if os.path.exists(POSTED_LINKS_FILE):
        try:
            with open(POSTED_LINKS_FILE, "r") as f:
                return set(json.load(f))
        except: return set()
    return set()

def save_posted_links(links: set):
    with open(POSTED_LINKS_FILE, "w") as f:
        json.dump(list(links), f)

posted_news_links = load_posted_links()

# --- 🌍 TILLAR BAZASI ---
texts = {
    "uz": {
        "welcome": "⛩️ {bold_name}, ANIVERSE OLAMIGA XUSH KELIBSIZ! ⛩️\n\nTilni o'zgartirish: /lang",
        "search_btn": "🔎 Anime Qidirish",
        "random_btn": "🎲 Tasodifiy Anime",
        "top_btn": "🌟 Top-5 Reyting",
        "news_btn": "📰 Yangiliklar",
        "order_btn": "📝 Anime Buyurtma",
        "score": "Reyting",
        "top_loading": "🏆 Yuklanmoqda...",
        "not_found": "🤷‍♂️ Hech narsa topilmadi.",
        "site_info": "\n🎬 @AniZoneHD — Biz bilan qoling!",
        "enter_name": "🔎 Anime nomini kiriting:",
        "error": "❌ Xato yuz berdi.",
        "footer": "\n\n📢 Kanal: @AniZoneHD\n🤖 Bot: @{bot}",
        "order_prompt": "✍️ Topilmagan anime nomini yozing. Biz uni bazaga qo'shishga harakat qilamiz:",
        "order_success": "✅ Buyurtmangiz adminga yetkazildi! Tez orada bazamizga qo'shiladi.",
    },
    "ru": {
        "welcome": "⛩️ {bold_name}, ДОБРО ПОЖАЛОВАТЬ В ANIVERSE! ⛩️\n\nСмена языка: /lang",
        "search_btn": "🔎 Поиск Аниме",
        "random_btn": "🎲 Случайное Аниме",
        "top_btn": "🌟 Топ-5 Рейтинг",
        "news_btn": "📰 Новости",
        "order_btn": "📝 Заказать Аниме",
        "score": "Рейтинг",
        "top_loading": "🏆 Загружаю...",
        "not_found": "🤷‍♂️ Ничего не найдено.",
        "site_info": "\n🎬 @AniZoneHD — Будь с нами!",
        "enter_name": "🔎 Введите название аниме:",
        "error": "❌ Произошла ошибка.",
        "footer": "\n\n📢 Kanal: @AniZoneHD\n🤖 Бот: @{bot}",
        "order_prompt": "✍️ Напишите название аниме, которое вы не нашли. Мы постараемся добавить его:",
        "order_success": "✅ Ваш заказ отправлен админу! Скоро добавим в нашу базу.",
    },
    "en": {
        "welcome": "⛩️ {bold_name}, WELCOME TO ANIVERSE! ⛩️\n\nChange language: /lang",
        "search_btn": "🔎 Search Anime",
        "random_btn": "🎲 Random Anime",
        "top_btn": "🌟 Top-5 Rating",
        "news_btn": "📰 News",
        "order_btn": "📝 Order Anime",
        "score": "Score",
        "top_loading": "🏆 Loading...",
        "not_found": "🤷‍♂️ Not found.",
        "site_info": "\n🎬 Stay with @AniZoneHD!",
        "enter_name": "🔎 Enter anime name:",
        "error": "❌ Error occurred.",
        "footer": "\n\n📢 Channel: @AniZoneHD\n🤖 Bot: @{bot}",
        "order_prompt": "✍️ Write the name of the anime you couldn't find. We'll try to add it:",
        "order_success": "✅ Your order has been sent to the admin! We will add it soon.",
    },
    "jp": {
        "welcome": "⛩️ {bold_name}、ANIVERSEへようこそ！⛩️\n\n言語変更: /lang",
        "search_btn": "🔎 アニメ検索",
        "random_btn": "🎲 ランダムアニメ",
        "top_btn": "🌟 トップ5レーティング",
        "news_btn": "📰 ニュース",
        "order_btn": "📝 アニメを注文",
        "score": "スコア",
        "top_loading": "🏆 読み込み中...",
        "not_found": "🤷‍♂️ 見つかりません。",
        "site_info": "\n🎬 @AniZoneHDと一緒にいてください!",
        "enter_name": "🔎 アニメ名を入力してください:",
        "error": "❌ エラーが発生しました。",
        "footer": "\n\n📢 チャンネル: @AniZoneHD\n🤖 ボット: @{bot}",
        "order_prompt": "✍️ 見つからなかったアニメの名前を書いてください。追加してみます:",
        "order_success": "✅ ご注文が管理者に送信されました！すぐにベースに追加します。",
    }
}

# --- 🛠 YORDAMCHI FUNKSIYALAR ---
def get_u_lang(user_id):
    return user_langs.get(user_id, "uz")

# 📊 STATISTIKA FUNKSIYALARI
def init_stats():
    """Statistika faylini boshlash"""
    db_file = "admin_stats.json"
    if not os.path.exists(db_file):
        with open(db_file, "w") as f:
            json.dump({"posts": 0, "trailers": 0, "api_searches": 0}, f)

def increment_stat(stat_name):
    """Statistikani oshirish"""
    db_file = "admin_stats.json"
    try:
        with open(db_file, "r") as f:
            stats = json.load(f)
    except:
        stats = {"posts": 0, "trailers": 0, "api_searches": 0}
    
    if stat_name in stats:
        stats[stat_name] += 1
    
    with open(db_file, "w") as f:
        json.dump(stats, f)

# Boshlash
init_stats()

async def translate_text(text, dest_lang):
    if not text: return text
    try:
        res = await asyncio.to_thread(translator.translate, text, dest=dest_lang)
        return res.text
    except: return text

async def fetch_shikimori_detail(session, anime_id):
    url = f"https://shikimori.one/api/animes/{anime_id}"
    headers = {"User-Agent": "ZAnimeRobot"}
    async with session.get(url, headers=headers) as resp:
        if resp.status == 200:
            return await resp.json()
    return None

async def format_smart_anime(anime_data, lang, session):
    if 'description' not in anime_data:
        full_data = await fetch_shikimori_detail(session, anime_data['id'])
        if full_data: anime_data = full_data

    title_en = anime_data.get('name', 'N/A')
    title_ru = anime_data.get('russian') or title_en
    jap_names = anime_data.get('japanese', [])
    title_jp = jap_names[0] if jap_names else title_en
    
    title_uz = await translate_text(title_ru, "uz")

    score = anime_data.get('score', 'N/A')
    synopsis_ru = re.sub(r'\[.*?\]', '', anime_data.get('description', '...') or '...')[:400] + "..."
    
    if lang == "uz": synopsis = await translate_text(synopsis_ru, "uz")
    elif lang == "en": synopsis = await translate_text(synopsis_ru, "en")
    else: synopsis = synopsis_ru

    t = texts.get(lang, texts["uz"])
    
    msg = f"🇯🇵 Jp: {html.bold(title_jp)}\n🇺🇸 Eng: {html.bold(title_en)}\n🇷🇺 Rus: {html.bold(title_ru)}\n🇺🇿 Uzb: {html.bold(title_uz)}\n\n"
    msg += f"⭐️ {t['score']}: {score}\n\n📖 {html.italic(synopsis)}\n{t['site_info']}"
    msg += t["footer"].format(bot=BOT_USERNAME)
    
    img_url = f"https://shikimori.one{anime_data.get('image', {}).get('original')}" if anime_data.get('image') else "https://i.ytimg.com/vi/5S_6uGf6bYk/maxresdefault.jpg"
    
    return msg, img_url, anime_data.get('status')

def get_smart_keyboard(anime_id, status, is_channel=False):
    if is_channel:
        first_btn = InlineKeyboardButton(text="🔍 Anime haqida ma'lumot", url=f"https://t.me/{BOT_USERNAME}")
    else:
        first_btn = InlineKeyboardButton(text="📢 Kanalga o'tish", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")

    buttons = [[first_btn]]
    
    if status in ['ongoing', 'released']:
        buttons.insert(0, [InlineKeyboardButton(text="🎬Tomosha qilish", url=f"https://t.me/{VIDEO_BOT_USERNAME}?start=anime_{anime_id}")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang_uz"),
         InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru"),
         InlineKeyboardButton(text="🇯🇵 日本語", callback_data="setlang_jp")]
    ])

def main_menu(lang):
    t = texts[lang]
    # ✅ BUYURTMA TUGMASI MENU'GA QO'SHILDI
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t["search_btn"]), KeyboardButton(text=t["random_btn"])],
        [KeyboardButton(text=t["top_btn"]), KeyboardButton(text=t["news_btn"])],
        [KeyboardButton(text=t["order_btn"])] 
    ], resize_keyboard=True)

def admin_menu():
    news_status = "🔴 Avto-postni to'xtatish" if news_posting_enabled else "🟢 Avto-postni yoqish"
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Kanalga post yaratish")],
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text=news_status)],
        [KeyboardButton(text="🏠 Asosiy menyu")]
    ], resize_keyboard=True)

def cancel_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)

# --- 🚀 HANDLERLAR ---
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("⛩️ ANIVERSE\n\nTilni tanlang / Выберите язык / 言語を選択してください:", reply_markup=lang_kb())

@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(call: CallbackQuery):
    lang = call.data.split("_")[1]
    user_langs[call.from_user.id] = lang
    await call.message.delete()
    await call.message.answer(texts[lang]["welcome"].format(bold_name=html.bold(call.from_user.full_name)), reply_markup=main_menu(lang))

@dp.message(Command("lang"))
async def cmd_lang(message: Message):
    await message.answer("🌍 Tilni tanlang / Выберите язык / 言語を選択してください:", reply_markup=lang_kb())

@dp.message(Command("stats"))
async def show_public_stats(message: Message, bot: Bot):
    """Barcha foydalanuvchilar uchun statistika"""
    try:
        channel_info = await bot.get_chat(CHANNEL_ID)
        channel_members = channel_info.members_count if hasattr(channel_info, 'members_count') else "N/A"
    except:
        channel_members = "N/A"
    
    # 📁 Saqlangan fayllarni hisoblash
    db_file = "admin_stats.json"
    if os.path.exists(db_file):
        try:
            with open(db_file, "r") as f:
                stats = json.load(f)
                posts_count = stats.get("posts", 0)
                trailers_count = stats.get("trailers", 0)
                api_searches = stats.get("api_searches", 0)
        except:
            posts_count = trailers_count = api_searches = 0
    else:
        posts_count = trailers_count = api_searches = 0
    
    stats_text = (
        f"📊 <b>ANIVERSE STATISTIKASI</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Kanal a'zolari:</b> {channel_members}\n"
        f"📝 <b>Yuborilgan postlar:</b> {posts_count}\n"
        f"🎬 <b>Treyler/Video:</b> {trailers_count}\n"
        f"🔍 <b>Izlanish so'rovlari:</b> {api_searches}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🎬 Kanalga obuna bo'ling: @AniZoneHD"
    )
    
    await message.answer(stats_text)

@dp.message(F.text.in_([texts["uz"]["news_btn"], texts["ru"]["news_btn"], texts["en"]["news_btn"], texts["jp"]["news_btn"]]))
async def get_news(message: Message):
    lang = get_u_lang(message.from_user.id)
    t = texts[lang]
    status_msg = await message.answer("🔄 Yangi animelar qidirilmoqda...")
    
    url = "https://shikimori.one/api/animes?limit=2&status=ongoing&order=popularity"
    headers = {"User-Agent": "ZAnimeRobot"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                new_animes = await resp.json()
                if not new_animes:
                    await message.answer(t["error"])
                else:
                    for anime in new_animes:
                        caption, img_url, a_status = await format_smart_anime(anime, lang, session)
                        kb = get_smart_keyboard(anime['id'], a_status, is_channel=False)
                        try:
                            await message.answer_photo(photo=URLInputFile(img_url), caption=caption, reply_markup=kb)
                        except: pass
                        await asyncio.sleep(0.5)
            else: await message.answer(t["error"])
    await status_msg.delete()

@dp.message(F.text.in_([texts["uz"]["search_btn"], texts["ru"]["search_btn"], texts["en"]["search_btn"], texts["jp"]["search_btn"]]))
async def search_init(message: Message):
    uid = message.from_user.id
    lang = get_u_lang(uid)
    if uid in order_waiting: order_waiting.remove(uid)
    search_waiting.add(uid)
    await message.answer(texts[lang]["enter_name"])

@dp.message(F.text.in_([texts["uz"]["order_btn"], texts["ru"]["order_btn"], texts["en"]["order_btn"], texts["jp"]["order_btn"]]))
async def order_init(message: Message):
    uid = message.from_user.id
    lang = get_u_lang(uid)
    if uid in search_waiting: search_waiting.remove(uid)
    order_waiting.add(uid)
    await message.answer(texts[lang]["order_prompt"], reply_markup=cancel_kb())

@dp.message(F.text.in_([texts["uz"]["random_btn"], texts["ru"]["random_btn"], texts["en"]["random_btn"], texts["jp"]["random_btn"]]))
async def random_anime(message: Message):
    lang = get_u_lang(message.from_user.id)
    status_msg = await message.answer("🎲 Qidirilmoqda...")
    
    url = "https://shikimori.one/api/animes?limit=1&order=random&status=released,ongoing"
    headers = {"User-Agent": "ZAnimeRobot"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as r:
            if r.status == 200:
                data = await r.json()
                if data:
                    caption, img_url, a_status = await format_smart_anime(data[0], lang, session)
                    kb = get_smart_keyboard(data[0]['id'], a_status, is_channel=False)
                    await message.answer_photo(URLInputFile(img_url), caption=caption, reply_markup=kb)
    await status_msg.delete()

@dp.message(F.text.in_([texts["uz"]["top_btn"], texts["ru"]["top_btn"], texts["en"]["top_btn"], texts["jp"]["top_btn"]]))
async def top_5(message: Message):
    lang = get_u_lang(message.from_user.id)
    await message.answer(texts[lang]["top_loading"])
    
    url = "https://shikimori.one/api/animes?limit=5&order=ranked"
    headers = {"User-Agent": "ZAnimeRobot"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as r:
            if r.status == 200:
                data = await r.json()
                for anime in data:
                    caption, img_url, a_status = await format_smart_anime(anime, lang, session)
                    kb = get_smart_keyboard(anime['id'], a_status, is_channel=False)
                    await message.answer_photo(URLInputFile(img_url), caption=caption, reply_markup=kb)
                    await asyncio.sleep(0.5)

# --- 🔑 ADMIN PANEL ---
@dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message):
    await message.answer("👑 Xush kelibsiz Admin!", reply_markup=admin_menu())

@dp.message(F.text == "🏠 Asosiy menyu", F.from_user.id == ADMIN_ID)
async def back_to_main(message: Message):
    admin_states.pop(message.from_user.id, None)
    lang = get_u_lang(message.from_user.id)
    await message.answer("Asosiy menyu.", reply_markup=main_menu(lang))

@dp.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def show_stats(message: Message, bot: Bot):
    # 📊 STATISTIKA OLISH
    try:
        channel_info = await bot.get_chat(CHANNEL_ID)
        channel_members = channel_info.members_count if hasattr(channel_info, 'members_count') else "N/A"
    except:
        channel_members = "N/A"
    
    # 📁 Saqlangan fayllarni hisoblash
    db_file = "admin_stats.json"
    if os.path.exists(db_file):
        try:
            with open(db_file, "r") as f:
                stats = json.load(f)
                posts_count = stats.get("posts", 0)
                trailers_count = stats.get("trailers", 0)
                api_searches = stats.get("api_searches", 0)
        except:
            posts_count = trailers_count = api_searches = 0
    else:
        posts_count = trailers_count = api_searches = 0
    
    stats_text = (
        f"📊 <b>ADMIN STATISTIKASI</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Kanal a'zolari:</b> {channel_members}\n"
        f"📝 <b>Postlar soni:</b> {posts_count}\n"
        f"🎬 <b>Treyler/Video:</b> {trailers_count}\n"
        f"🔍 <b>API qidiruvlari:</b> {api_searches}\n"
        f"━━━━━━━━━━━━━━━━━"
    )
    
    await message.answer(stats_text, reply_markup=admin_menu())

@dp.message(F.text == "❌ Bekor qilish", F.from_user.id == ADMIN_ID)
async def cancel_admin_action(message: Message):
    admin_states.pop(message.from_user.id, None)
    await message.answer("🚫 Barcha amallar bekor qilindi.", reply_markup=admin_menu())

@dp.message(F.text.in_(["🔴 Avto-postni to'xtatish", "🟢 Avto-postni yoqish"]), F.from_user.id == ADMIN_ID)
async def toggle_news(message: Message):
    global news_posting_enabled
    news_posting_enabled = not news_posting_enabled
    txt = "yoqildi ✅" if news_posting_enabled else "o'chirildi ❌"
    await message.answer(f"Yangiliklar avto-posti {txt}", reply_markup=admin_menu())

@dp.message(F.text == "📝 Kanalga post yaratish", F.from_user.id == ADMIN_ID)
async def start_media_post(message: Message):
    admin_states[message.from_user.id] = {"step": "waiting_media"}
    await message.answer("📸 Rasm yoki 🎥 Qisqa video (Treyler) yuboring:", reply_markup=cancel_kb())

@dp.message(F.from_user.id == ADMIN_ID, F.photo | F.video | F.document)
async def handle_admin_media(message: Message):
    state = admin_states.get(message.from_user.id)
    if state and state.get("step") == "waiting_media":
        if message.photo:
            state["file_id"] = message.photo[-1].file_id
            state["media_type"] = "photo"
        elif message.video:
            state["file_id"] = message.video.file_id
            state["media_type"] = "video"
        elif message.document and message.document.mime_type.startswith('video/'):
            state["file_id"] = message.document.file_id
            state["media_type"] = "video"
        else:
            return await message.answer("⚠️ Iltimos, rasm yoki video yuboring.")
            
        state["step"] = "waiting_id"
        await message.answer("✅ Qabul qilindi!\n\nEndi bu anime uchun o'z ID raqamini (yoki Shikimori ID) kiriting.\n(Bu Tomosha qilish tugmasini yasash uchun kerak)")

# 🚀 ASOSIY MATN QABUL QILUVCHI FUNKSIYA
@dp.message(F.text)
async def handle_all_text(message: Message, bot: Bot):
    uid = message.from_user.id
    lang = get_u_lang(uid)
    
    # --- 1. ADMIN HOLATI ---
    if uid == ADMIN_ID:
        state = admin_states.get(uid)
        if state and state.get("step") == "waiting_id":
            if not message.text.strip().isdigit():
                return await message.answer("⚠️ Faqat raqam kiriting!")
            state["anime_id"] = message.text.strip()
            state["step"] = "waiting_caption"
            return await message.answer("✅ ID saqlandi!\n\nEndi anime haqidagi ma'lumotni (Matn/Caption) yuboring:")
            
        elif state and state.get("step") == "waiting_caption":
            anime_id = state.get("anime_id", "0")
            caption_text = message.text
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎬Tomosha qilish", url=f"https://t.me/{VIDEO_BOT_USERNAME}?start=watch_{anime_id}")],
                [InlineKeyboardButton(text="🔍Anime haqida ma'lumot", url=f"https://t.me/{BOT_USERNAME}")]
            ])
            try:
                if state.get("media_type") == "photo":
                    await bot.send_photo(CHANNEL_ID, photo=state["file_id"], caption=caption_text, reply_markup=kb)
                else:
                    await bot.send_video(CHANNEL_ID, video=state["file_id"], caption=caption_text, reply_markup=kb)
                await message.answer("🎉 Post muvaffaqiyatli kanalga joylandi!", reply_markup=admin_menu())
            except Exception as e:
                await message.answer(f"❌ Xato yuz berdi: {e}")
            admin_states.pop(uid, None)
            return
            
        if message.text in ["📝 Kanalga post yaratish", "🔴 Avto-postni to'xtatish", "🟢 Avto-postni yoqish", "🏠 Asosiy menyu", "❌ Bekor qilish"]:
            return 
            
    # --- 2. ANIME BUYURTMA (Foydalanuvchi buyurtma yozmasa) ---
    if uid in order_waiting:
        order_waiting.remove(uid)
        user_link = f"@{message.from_user.username}" if message.from_user.username else f'<a href="tg://user?id={uid}">{message.from_user.full_name}</a>'
        admin_msg = f"📩 <b>YANGI BUYURTMA</b>\n\n👤 <b>Kimdan:</b> {user_link}\n🆔 <b>ID:</b> <code>{uid}</code>\n\n💬 <b>Anime nomi:</b> {message.text}"
        try:
            await bot.send_message(ADMIN_ID, admin_msg)
        except: pass
        return await message.answer(texts[lang]["order_success"], reply_markup=main_menu(lang))

    # --- 3. ODDIY QIDIRUV ---
    if uid in search_waiting:
        search_waiting.remove(uid)
        
    status_msg = await message.answer("🔍 Qidirilmoqda...")
    url = f"https://shikimori.one/api/animes?search={quote(message.text)}&limit=1"
    headers = {"User-Agent": "ZAnimeRobot"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as r:
            if r.status == 200:
                data = await r.json()
                if data:
                    increment_stat("api_searches")  # 📊 Statistika yangilash
                    caption, img_url, a_status = await format_smart_anime(data[0], lang, session)
                    kb = get_smart_keyboard(data[0]['id'], a_status, is_channel=False)
                    try:
                        shiki_photo_obj = URLInputFile(img_url) if img_url.startswith("http") else img_url
                        await message.answer_photo(shiki_photo_obj, caption=caption, reply_markup=kb)
                    except:
                        await message.answer(caption, reply_markup=kb)
                else:
                    await message.answer(texts[lang]["not_found"])
            else:
                await message.answer(texts[lang]["error"])
    await status_msg.delete()


# --- 🛰 AVTO-POST KANAL UCHUN ---
async def post_random_anime_to_channel(bot: Bot):
    if not news_posting_enabled: return
    try:
        url = "https://shikimori.one/api/animes?limit=1&order=random&status=released,ongoing"
        headers = {"User-Agent": "ZAnimeRobot"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                if r.status == 200:
                    data = await r.json()
                    if data:
                        anime = data[0]
                        full_data = await fetch_shikimori_detail(session, anime['id'])
                        if full_data: anime = full_data
                        
                        title_en = anime.get('name', 'N/A')
                        title_ru = anime.get('russian') or title_en
                        jap_names = anime.get('japanese', [])
                        title_jp = jap_names[0] if jap_names else title_en
                        title_uz = await translate_text(title_ru, "uz")
                        score = anime.get('score', 'N/A')
                        
                        post_text = f"🎲 {html.bold('KUN TASODIFIY ANIMESI')}\n\n"
                        post_text += f"🇯🇵 Jp: {html.bold(title_jp)}\n"
                        post_text += f"🇺🇸 Eng: {html.bold(title_en)}\n"
                        post_text += f"🇷🇺 Rus: {html.bold(title_ru)}\n"
                        post_text += f"🇺🇿 Uzb: {html.bold(title_uz)}\n\n"
                        post_text += f"⭐️ Reyting: {score}\n\n🤖 Bot: @{BOT_USERNAME}"
                        
                        img_url = f"https://shikimori.one{anime.get('image', {}).get('original')}"
                        kb = get_smart_keyboard(anime['id'], anime.get('status'), is_channel=True)
                        
                        try:
                            await bot.send_photo(CHANNEL_ID, photo=URLInputFile(img_url), caption=post_text, reply_markup=kb)
                        except: pass
    except Exception as e: logger.error(f"Random post xatosi: {e}")

async def check_and_post_news(bot: Bot):
    if not news_posting_enabled: return
    global posted_news_links
    
    url = "https://shikimori.one/api/animes?limit=3&status=ongoing&order=popularity"
    headers = {"User-Agent": "ZAnimeRobot"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    new_animes = await resp.json()
                    for anime in reversed(new_animes):
                        anime_id = str(anime['id'])
                        if anime_id not in posted_news_links:
                            full_data = await fetch_shikimori_detail(session, anime['id'])
                            if full_data: anime = full_data
                            
                            title_en = anime.get('name', 'N/A')
                            title_ru = anime.get('russian') or title_en
                            title_uz = await translate_text(title_ru, "uz")
                            
                            post_text = f"📰 {html.bold('YANGI QISMLAR / ONGOING')}\n\n"
                            post_text += f"🇺🇸 {html.bold(title_en)}\n"
                            post_text += f"🇷🇺 {html.bold(title_ru)}\n"
                            post_text += f"🇺🇿 {html.bold(title_uz)}\n\n"
                            post_text += f"🤖 Bot: @{BOT_USERNAME}"
                            
                            img_url = f"https://shikimori.one{anime.get('image', {}).get('original')}"
                            kb = get_smart_keyboard(anime['id'], anime.get('status'), is_channel=True)
                            
                            try:
                                await bot.send_photo(chat_id=CHANNEL_ID, photo=URLInputFile(img_url), caption=post_text, reply_markup=kb)
                            except: pass
                            
                            posted_news_links.add(anime_id)
                            save_posted_links(posted_news_links)
                            break
    except Exception as e: logger.error(f"News post xatosi: {e}")

async def news_loop(bot: Bot):
    while True:
        await check_and_post_news(bot)
        await asyncio.sleep(43200)  
        await post_random_anime_to_channel(bot)
        await asyncio.sleep(43200)
        
async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    asyncio.create_task(news_loop(bot))
    logger.info("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())