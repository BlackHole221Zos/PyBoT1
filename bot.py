from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import aiohttp
from bs4 import BeautifulSoup
import logging
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = '7680940661:AAHVMKA6wfF9TN2XIPoMV8bJO-34euXJ1os'  # Замените на реальный токен!
ADMIN_IDS = [991357162]  # Замените на ваш ID

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальные переменные
user_data = {}
broadcast_mode = False

# КЛАВИАТУРЫ 
def create_start_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="▶️ Начать")]],
        resize_keyboard=True
    )

def create_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Видео на Rutube"), KeyboardButton(text="🎵 Музыка на Bandcamp")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="❌ Очистить историю")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

def create_menu_only_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )

def create_search_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Искать ещё", callback_data="more"),
                InlineKeyboardButton(text="Новый поиск", callback_data="new")
            ],
            [InlineKeyboardButton(text="Закончить", callback_data="stop")]
        ]
    )

def create_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

# ПОИСК
async def find_videos(query: str):
    url = f"https://rutube.ru/api/search/video/?query={query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return [(item.get("title", "Без названия"), f"https://rutube.ru/video/{item.get('id')}/") for item in data.get("results", [])]
            logger.error(f"Ошибка запроса: {response.status}")
    return []

async def find_music(query: str):
    url = f"https://bandcamp.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                soup = BeautifulSoup(await response.text(), 'html.parser')
                return [(item.find('div', {'class': 'heading'}).text.strip(), item.find('a')['href']) for item in soup.find_all('li', {'class': 'searchresult'})]
            logger.error(f"Ошибка запроса: {response.status}")
    return []

#ОБРАБОТЧИКИ 
@dp.message(Command("start"))
async def start_bot(message: types.Message):
    name = message.from_user.first_name
    await message.answer(f"Привет, {name}!\nЯ бот для поиска видео и музыки. Нажми «▶️ Начать»", reply_markup=create_start_keyboard())

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return
    await message.answer("⚙️ Админ-панель:", reply_markup=create_admin_keyboard())

@dp.message(lambda message: message.text == "▶️ Начать")
async def start_search(message: types.Message):
    await message.answer("Выбери тип поиска:", reply_markup=create_main_menu())

@dp.message(lambda message: message.text == "🏠 Главное меню")
async def return_to_menu(message: types.Message):
    await message.answer("Главное меню:", reply_markup=create_main_menu())

@dp.message(lambda message: message.text in ["🎥 Видео на Rutube", "🎵 Музыка на Bandcamp"])
async def choose_search_type(message: types.Message):
    chat_id = message.chat.id
    user_data[chat_id] = {"history": [], "results": [], "index": 0, "type": None}
    user_data[chat_id]["type"] = "video" if message.text == "🎥 Видео на Rutube" else "music"
    await message.answer(f"Ищем {'видео' if user_data[chat_id]['type'] == 'video' else 'музыку'}. Введите запрос:", reply_markup=create_menu_only_keyboard())

@dp.message(lambda message: message.text == "📊 Статистика")
async def show_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return
    await message.answer(f"👥 Пользователей: {len(user_data)}")

@dp.message(lambda message: message.text == "📢 Рассылка")
async def start_broadcast(message: types.Message):
    global broadcast_mode
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return
    broadcast_mode = True
    await message.answer("Введите сообщение для рассылки:")

@dp.message(lambda message: message.text == "🔙 Назад")
async def admin_back(message: types.Message):
    await message.answer("Главное меню:", reply_markup=create_main_menu())

@dp.message()
async def process_query(message: types.Message):
    global broadcast_mode
    chat_id = message.chat.id
    text = message.text.strip()

    # Режим рассылки
    if broadcast_mode and message.from_user.id in ADMIN_IDS:
        broadcast_mode = False
        success = 0
        for user_id in user_data:
            try:
                await bot.send_message(user_id, text)
                success += 1
            except:
                pass
        await message.answer(f"✅ Рассылка отправлена {success} пользователям")
        return

    # Основная логика
    if text == "📜 История":
        history = "\n".join(user_data.get(chat_id, {}).get("history", []))
        await message.answer(f"📖 История:\n{history or 'Пусто'}")
    
    elif text == "❌ Очистить историю":
        user_data[chat_id] = {"history": [], "results": [], "index": 0, "type": None}
        await message.answer("🗑 История очищена")
    
    elif chat_id in user_data and user_data[chat_id].get("type"):
        # Поиск контента
        user_data[chat_id]["history"].append(text)
        results = await (find_videos(text) if user_data[chat_id]["type"] == "video" else find_music(text))
        
        if results:
            user_data[chat_id]["results"] = results
            user_data[chat_id]["index"] = 0
            await show_result(chat_id, message)
        else:
            await message.answer("😞 Ничего не найдено")
    
    else:
        await message.answer("⚠️ Сначала выберите тип поиска")

#ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ 
async def show_result(chat_id: int, message: types.Message = None):
    result = user_data[chat_id]["results"][user_data[chat_id]["index"]]
    text = f"🔍 Результат:\n<b>{result[0]}</b>\n🌐 Ссылка: {result[1]}"
    await (message.answer if message else bot.send_message)(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=create_search_buttons())

@dp.callback_query(lambda c: c.data in ["more", "new", "stop"])
async def handle_callbacks(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    data = callback.data
    
    if data == "more":
        user_data[chat_id]["index"] += 1
        if user_data[chat_id]["index"] >= len(user_data[chat_id]["results"]):
            await callback.answer("❌ Больше результатов нет")
            return
        await show_result(chat_id)
    
    elif data == "new":
        await callback.message.answer("Введите новый запрос:")
    
    elif data == "stop":
        user_data[chat_id] = {"history": [], "results": [], "index": 0, "type": None}
        await callback.message.answer("Поиск остановлен", reply_markup=create_main_menu())
    
    await callback.answer()

#ЗАПУСК
async def run_bot():
    try:
        logger.info("Бот запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"ОШИБКА: {e}")

if __name__ == '__main__':
    asyncio.run(run_bot())
