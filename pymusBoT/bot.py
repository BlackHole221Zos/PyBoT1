from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import aiohttp
from bs4 import BeautifulSoup
import logging
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = '7761632211:AAHHq5P9SHI-FnZcqsckZ90mOL3ZbCZUL5s'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальные переменные для хранения результатов поиска
search_results = {}  # {user_id: [(track_name, track_link), ...]}
current_index = {}   # {user_id: index}

# Клавиатура с кнопкой "Начать"
def get_start_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Начать")]],
        resize_keyboard=True  # Клавиатура подстраивается под размер экрана
    )

# Клавиатура для управления поиском
def get_search_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Искать ещё", callback_data="search_more"),
            InlineKeyboardButton(text="Искать другую песню", callback_data="new_search")
        ]
    ])

# Поиск музыки на Bandcamp
async def search_music(query: str):
    url = f"https://bandcamp.com/search?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        logger.info(f"Поиск музыки по запросу: {query}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    # Парсим результаты поиска
                    results = soup.find_all('li', {'class': 'searchresult'})
                    if results:
                        tracks = []
                        for result in results:
                            track_name = result.find('div', {'class': 'heading'}).text.strip()
                            track_link = result.find('a')['href']
                            tracks.append((track_name, track_link))
                        logger.info(f"Найдено {len(tracks)} треков.")
                        return tracks
                    else:
                        logger.warning("Треки не найдены.")
                else:
                    logger.error(f"Ошибка запроса: {response.status}")
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")

    return None

# Обработчик команды /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    logger.info(f"Пользователь {message.from_user.id} запустил бота.")
    await message.answer(
        "Привет! Я музыкальный бот. Напиши название песни или исполнителя, и я найду её для тебя. Пример The Rolling Stones Paint It, Black",
        parse_mode=ParseMode.HTML,
        reply_markup=get_start_keyboard()
    )

# Обработчик текстовых сообщений
@dp.message()
async def handle_message(message: types.Message):
    query = message.text.strip()
    logger.info(f"Пользователь {message.from_user.id} запросил: {query}")

    # Если пользователь нажал "Начать", отправляем приветствие
    if query.lower() == "начать":
        await send_welcome(message)
        return

    # Ищем треки
    tracks = await search_music(query)
    if not tracks:
        await message.answer(
            "😔 Не удалось найти песню. Попробуй другой запрос.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_start_keyboard()
        )
        return

    # Сохраняем результаты и отправляем первый трек
    search_results[message.from_user.id] = tracks
    current_index[message.from_user.id] = 0
    await send_track(message.from_user.id, message)

# Отправка трека пользователю
async def send_track(user_id: int, message: types.Message = None):
    if user_id not in search_results or user_id not in current_index:
        logger.warning("Результаты поиска отсутствуют.")
        return

    track_name, track_link = search_results[user_id][current_index[user_id]]
    logger.info(f"Отправляю трек пользователю {user_id}: {track_name}")

    if message:
        await message.answer(
            f"🎵 Найдена песня: <b>{track_name}</b>\n🔗 Ссылка: {track_link}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_search_keyboard()
        )
    else:
        await bot.send_message(
            user_id,
            f"🎵 Найдена песня: <b>{track_name}</b>\n🔗 Ссылка: {track_link}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_search_keyboard()
        )

# Обработчик кнопки "Искать ещё"
@dp.callback_query(lambda callback: callback.data == "search_more")
async def handle_search_more(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"Пользователь {user_id} нажал 'Искать ещё'.")

    if user_id not in search_results or user_id not in current_index:
        await callback.answer("Результаты поиска устарели. Начни новый поиск.")
        return

    # Переход к следующему треку
    current_index[user_id] += 1
    if current_index[user_id] >= len(search_results[user_id]):
        await callback.answer("Больше результатов нет.")
        return

    await send_track(user_id)
    await callback.answer()

# Обработчик кнопки "Искать другую песню"
@dp.callback_query(lambda callback: callback.data == "new_search")
async def handle_new_search(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"Пользователь {user_id} нажал 'Искать другую песню'.")

    # Сбрасываем результаты поиска
    if user_id in search_results:
        del search_results[user_id]
    if user_id in current_index:
        del current_index[user_id]

    await callback.message.answer(
        "Введите название песни или исполнителя для нового поиска:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_start_keyboard()
    )
    await callback.answer()

# Запуск бота
async def main():
    try:
        logger.info("Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    asyncio.run(main())