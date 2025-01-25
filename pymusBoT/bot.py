from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import aiohttp
from bs4 import BeautifulSoup
import logging
import asyncio
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = 'ВАШ_ТОКЕН_БОТАs'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальные переменные для хранения данных
search_results = {}  # Результаты поиска
current_index = {}   # Текущий индекс результата
search_type = {}     # Тип поиска (видео или музыка)
cooldowns = {}       # Кулдаун для чатов
search_history = {}  # История запросов

# Функция для обновления истории запросов
def update_search_history(chat_id: int, query: str):
    if chat_id not in search_history:
        search_history[chat_id] = []
    search_history[chat_id].append(query)
    # Ограничим историю последними 10 запросами
    if len(search_history[chat_id]) > 10:
        search_history[chat_id] = search_history[chat_id][-10:]

# Клавиатуры
def get_start_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="▶️ Начать")],
            [KeyboardButton(text="🎥 Искать видео на Rutube")],
            [KeyboardButton(text="🎵 Искать музыку на Bandcamp")],
            [KeyboardButton(text="📜 История запросов")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_search_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Искать ещё", callback_data="search_more"),
            InlineKeyboardButton(text="Искать другую песню", callback_data="new_search")
        ],
        [
            InlineKeyboardButton(text="Не хочу искать", callback_data="stop_search")
        ]
    ])

# Поиск видео на Rutube
async def search_video(query: str):
    url = f"https://rutube.ru/api/search/video/?query={query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return [(result.get("title", "Без названия"), f"https://rutube.ru/video/{result.get('id')}/") for result in data.get("results", [])]
            logger.error(f"Ошибка запроса: {response.status}")
    return None

# Поиск музыки на Bandcamp
async def search_music(query: str):
    url = f"https://bandcamp.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                soup = BeautifulSoup(await response.text(), 'html.parser')
                return [(result.find('div', {'class': 'heading'}).text.strip(), result.find('a')['href']) for result in soup.find_all('li', {'class': 'searchresult'})]
            logger.error(f"Ошибка запроса: {response.status}")
    return None

# Обработчик команды /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer(
        "Привет! Я музыкальный бот. Нажми «▶️ Начать», чтобы выбрать тип поиска.",
        reply_markup=get_start_keyboard()
    )

# Обработчик кнопки "Начать"
@dp.message(lambda message: message.text == "▶️ Начать")
async def handle_start(message: types.Message):
    await message.answer(
        "Выбери, что ты хочешь искать:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎥 Искать видео на Rutube")],
                [KeyboardButton(text="🎵 Искать музыку на Bandcamp")]
            ],
            resize_keyboard=True
        )
    )

# Обработчик кнопки "Главное меню"
@dp.message(lambda message: message.text == "🏠 Главное меню")
async def handle_main_menu(message: types.Message):
    await message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=get_start_keyboard()
    )

# Обработчик выбора типа поиска
@dp.message(lambda message: message.text in ["🎥 Искать видео на Rutube", "🎵 Искать музыку на Bandcamp"])
async def handle_search_type(message: types.Message):
    chat_id = message.chat.id
    search_type[chat_id] = "video" if message.text == "🎥 Искать видео на Rutube" else "music"
    await message.answer(
        f"Отлично! Теперь я буду искать {'видео на Rutube' if search_type[chat_id] == 'video' else 'музыку на Bandcamp'}. Введи название песни или исполнителя Пример The Rolling Stones Paint It, Black:",
        reply_markup=get_start_keyboard()
    )

# Обработчик текстовых сообщений
@dp.message()
async def handle_message(message: types.Message):
    chat_id = message.chat.id
    query = message.text.strip()

    if query == "📜 История запросов":
        if chat_id in search_history and search_history[chat_id]:
            history_text = "Недавно вы искали:\n"
            for i, query in enumerate(search_history[chat_id], 1):
                history_text += f"{i}. {query}\n"
            await message.answer(history_text)
        else:
            await message.answer("Вы ещё ничего не искали.")
        return

    if query == "🏠 Главное меню":
        await handle_main_menu(message)
        return

    if chat_id not in search_type:
        await message.answer("Сначала выбери тип поиска: видео или музыку.", reply_markup=get_start_keyboard())
        return

    # Добавляем запрос в историю
    update_search_history(chat_id, query)

    results = await (search_video(query) if search_type[chat_id] == "video" else search_music(query))

    if not results:
        await message.answer("😔 Не удалось найти результаты. Попробуй другой запрос.", reply_markup=get_start_keyboard())
        return

    search_results[chat_id] = results
    current_index[chat_id] = 0
    await send_result(chat_id, message)

# Отправка результата пользователю
async def send_result(chat_id: int, message: types.Message = None):
    if chat_id not in search_results or chat_id not in current_index:
        return

    result_name, result_link = search_results[chat_id][current_index[chat_id]]
    text = f"🎵 Найдено: <b>{result_name}</b>\n🔗 Ссылка: {result_link}"
    if message:
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_search_keyboard())
    else:
        await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=get_search_keyboard())

# Обработчик кнопки "Искать ещё"
@dp.callback_query(lambda callback: callback.data == "search_more")
async def handle_search_more(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id

    if chat_id in cooldowns and datetime.now() < cooldowns[chat_id]:
        await callback.answer("Подождите 5 секунд...")
        return

    if chat_id not in search_results or chat_id not in current_index:
        await callback.answer("Результаты поиска устарели. Начни новый поиск.")
        return

    current_index[chat_id] += 1
    if current_index[chat_id] >= len(search_results[chat_id]):
        await callback.answer("Больше результатов нет.")
        return

    cooldowns[chat_id] = datetime.now() + timedelta(seconds=5)
    await callback.answer("Нажимайте!")
    await send_result(chat_id)

# Обработчик кнопки "Искать другую песню"
@dp.callback_query(lambda callback: callback.data == "new_search")
async def handle_new_search(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id

    if chat_id in cooldowns and datetime.now() < cooldowns[chat_id]:
        await callback.answer("Подождите 5 секунд...")
        return

    if chat_id in search_results:
        del search_results[chat_id]
    if chat_id in current_index:
        del current_index[chat_id]

    cooldowns[chat_id] = datetime.now() + timedelta(seconds=5)
    await callback.answer("Нажимайте!")
    await callback.message.answer("Введите название песни или исполнителя для нового поиска. Пример The Rolling Stones Paint It, Black:", reply_markup=get_start_keyboard())

# Обработчик кнопки "Не хочу искать"
@dp.callback_query(lambda callback: callback.data == "stop_search")
async def handle_stop_search(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id

    # Очищаем данные пользователя
    if chat_id in search_results:
        del search_results[chat_id]
    if chat_id in current_index:
        del current_index[chat_id]
    if chat_id in search_type:
        del search_type[chat_id]

    await callback.answer("Поиск завершён.")
    await callback.message.answer(
        "Хорошо, поиск завершён. Если захочешь искать что-то ещё, просто нажми «▶️ Начать».",
        reply_markup=get_start_keyboard()
    )

# Запуск бота
async def main():
    try:
        logger.info("Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    asyncio.run(main())
