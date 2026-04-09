import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8594089178:AAGbUzm0Cbe9Dx_dzHVe-M-ehQfNMTj1Reo'
ADMIN_ID = 8599142466  
CHANNELS = ["@kinoscope1_uz"] 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect("kinobaza.db")
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS movies 
                   (id TEXT PRIMARY KEY, name TEXT, file_id TEXT, type TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# --- ADMIN HOLATLARI ---
class AdminState(StatesGroup):
    add_movie_id = State()
    add_movie_name = State()
    add_movie_video = State()
    del_movie = State()
    send_ads = State()

# --- ADMIN PANEL TUGMALARI ---
def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎬 Kino boshqaruvi", "📊 Statistika")
    markup.add("📢 Xabar yuborish")
    return markup

# --- OBUNA TEKSHIRISH ---
async def check_subscription(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status == 'left':
                return False
        except Exception:
            return False
    return True

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    conn = sqlite3.connect("kinobaza.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()

    if not await check_subscription(message.from_user.id):
        btn = InlineKeyboardMarkup(row_width=1)
        btn.add(InlineKeyboardButton("Kanalga a'zo bo'lish ➕", url="https://t.me/kinoscope1_uz"))
        btn.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        await message.answer("<b>Botdan foydalanish uchun kanalimizga obuna bo'ling!</b>", reply_markup=btn)
        return

    if message.from_user.id == ADMIN_ID:
        await message.answer("<b>Xush kelibsiz, Admin!</b>", reply_markup=admin_keyboard())
    else:
        await message.answer("<b>Kino kodini kiriting:</b>")

@dp.callback_query_handler(text="add_m")
async def add_movie_start(call: types.CallbackQuery):
    await call.message.answer("Kino uchun yangi kod (ID) yuboring:")
    await AdminState.add_movie_id.set()

@dp.message_handler(state=AdminState.add_movie_id)
async def add_id(message: types.Message, state: FSMContext):
    await state.update_data(m_id=message.text)
    await message.answer("Kino nomini yuboring:")
    await AdminState.add_movie_name.set()

@dp.message_handler(state=AdminState.add_movie_name)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(m_name=message.text)
    await message.answer("Kinoni (video faylini) yuboring:")
    await AdminState.add_movie_video.set()

@dp.message_handler(content_types=['video'], state=AdminState.add_movie_video)
async def add_video(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("kinobaza.db")
    conn.execute("INSERT INTO movies (id, name, file_id, type) VALUES (?, ?, ?, ?)",
                 (data['m_id'], data['m_name'], message.video.file_id, "kino"))
    conn.commit()
    await message.answer(f"✅ <b>Kino saqlandi!</b>\nID: {data['m_id']}")
    await state.finish()

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID, text="📊 Statistika")
async def stats(message: types.Message):
    conn = sqlite3.connect("kinobaza.db")
    m_count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    u_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await message.answer(f"📊 <b>Statistika:</b>\n\n🎬 Kinolar: {m_count} ta\n👤 Foydalanuvchilar: {u_count} ta")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID, text="🎬 Kino boshqaruvi")
async def movie_manage(message: types.Message):
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(InlineKeyboardButton("➕ Qo'shish", callback_data="add_m"),
            InlineKeyboardButton("❌ O'chirish", callback_data="del_m"))
    await message.answer("Boshqaruv:", reply_markup=btn)

@dp.callback_query_handler(text="check")
async def check_callback(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Obuna tasdiqlandi! Kino kodini yuboring:")
    else:
        await call.answer("❌ Hali a'zo emassiz!", show_alert=True)

@dp.message_handler()
async def search_movie(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await start_cmd(message)
        return
    
    conn = sqlite3.connect("kinobaza.db")
    res = conn.execute("SELECT * FROM movies WHERE id=?", (message.text,)).fetchone()
    if res:
        await message.answer_video(res[2], caption=f"🎬 <b>Nomi:</b> {res[1]}\n🆔 <b>Kodi:</b> {res[0]}")
    else:
        if message.from_user.id != ADMIN_ID:
            await message.answer("😔 <b>Kino topilmadi.</b>")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
                           
