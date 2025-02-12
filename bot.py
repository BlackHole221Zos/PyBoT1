from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import logging
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = 'YOUR_BOT_TOKEN'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data = {}

DONATE_URL = "https://www.donationalerts.com/r/black_h0le_d"  # Ссылка на донат
RUTUBE_DOWNLOAD_SITE = "https://cobalt.tools/?url="  # Сайт для скачивания видео с Rutube


def save_user_query(chat_id: int, query: str):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "history": [],
            "results": [],
            "index": 0,
            "type": None,
            "favorites": [],
            "settings": {"default_platform": None},
            "is_searching": False
        }
    if user_data[chat_id]["is_searching"]:
        user_data[chat_id]["history"].append(query)
        if len(user_data[chat_id]["history"]) > 10:
            user_data[chat_id]["history"] = user_data[chat_id]["history"][-10:]


def create_start_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="▶️ Начать")]],
        resize_keyboard=True
    )


def create_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Видео на Rutube"), KeyboardButton(text="🎵 Музыка на Bandcamp")],
            [KeyboardButton(text="⭐ Избранное"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="❌ Очистить историю")],
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="💰 Донат")]  # Добавлена кнопка доната
        ],
        resize_keyboard=True
    )


@dp.message(Command("start"))
async def start_bot(message: types.Message):
    name = message.from_user.first_name
    username = message.from_user.username
    greeting = f"Привет, {name}!" + (f" (@{username})" if username else "")
    await message.answer(greeting)
    await message.answer("Я бот для поиска видео и музыки. Нажми «▶️ Начать», чтобы выбрать тип поиска.",
                         reply_markup=create_start_keyboard())


@dp.message(lambda message: message.text == "▶️ Начать")
async def start_search(message: types.Message):
    await message.answer("Выбери, что ты хочешь искать:", reply_markup=create_main_menu())


@dp.message(lambda message: message.text in ["🎥 Видео на Rutube", "🎵 Музыка на Bandcamp"])
async def choose_search_type(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {
            "history": [],
            "results": [],
            "index": 0,
            "type": None,
            "favorites": [],
            "settings": {"default_platform": None},
            "is_searching": True
        }
    else:
        user_data[chat_id]["is_searching"] = True
    user_data[chat_id]["type"] = "video" if message.text == "🎥 Видео на Rutube" else "music"
    await message.answer(
        f"Отлично! Теперь я буду искать {'видео на Rutube' if user_data[chat_id]['type'] == 'video' else 'музыку на Bandcamp'}. Введи запрос:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True))


@dp.message(lambda message: message.text == "💰 Донат")
async def donate_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Перейти к донату", url=DONATE_URL)]
        ]
    )
    await message.answer(
        "Спасибо за поддержку! Ваш вклад помогает развивать проект. Вы можете сделать донат, нажав на кнопку ниже:",
        reply_markup=keyboard
    )


@dp.message()
async def process_query(message: types.Message):
    chat_id = message.chat.id
    query = message.text.strip()
    if query == "🏠 Главное меню":
        await return_to_menu(message)
        return
    if chat_id not in user_data or not user_data[chat_id]["type"]:
        await message.answer("Сначала выбери тип поиска.", reply_markup=create_main_menu())
        return
    if user_data[chat_id]["is_searching"]:
        save_user_query(chat_id, query)
    if user_data[chat_id]["type"] == "video":
        results = await find_videos(query)
    elif user_data[chat_id]["type"] == "music":
        results = await find_music(query)
    if not results:
        await message.answer("Ничего не найдено. Попробуй другой запрос.", reply_markup=create_main_menu())
        return
    user_data[chat_id]["results"] = results
    await show_results(chat_id, message)


async def find_videos(query: str):
    url = f"https://rutube.ru/api/search/video/?query={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return [(item.get("title", "Без названия"), f"https://rutube.ru/video/{item.get('id')}/") for item in
                        data.get("results", [])]
            logger.error(f"Ошибка запроса: {response.status}")
    return []


async def find_music(query: str):
    url = f"https://bandcamp.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                soup = BeautifulSoup(await response.text(), 'html.parser')
                return [(item.find('div', {'class': 'heading'}).text.strip(), item.find('a')['href']) for item in
                        soup.find_all('li', {'class': 'searchresult'})]
            logger.error(f"Ошибка запроса: {response.status}")
    return []


async def show_results(chat_id: int, message: types.Message = None):
    results = user_data[chat_id]["results"]
    if not results:
        await bot.send_message(chat_id, "Ничего не найдено.")
        return
    max_results_to_show = 10
    total_results = len(results)
    pages = [results[i:i + max_results_to_show] for i in range(0, total_results, max_results_to_show)]
    current_page = user_data[chat_id].get("current_page", 0)
    user_data[chat_id]["current_page"] = current_page
    for idx, result in enumerate(pages[current_page], start=current_page * max_results_to_show + 1):
        text = f"🔍 Результат {idx}/{total_results}\n"
        text += f"📌 Название: {result[0]}\n🔗 Ссылка: {result[1]}"
        # Создаем инлайн-клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        if user_data[chat_id]["type"] == "video":  # Add download link only for videos
            if not result[1].startswith("http"):
                result[1] = f"https://rutube.ru{result[1]}"
            download_link = f"{RUTUBE_DOWNLOAD_SITE}{result[1]}"
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text="⬇️ Скачать", url=download_link)]
            )
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(text="⭐ В избранное", callback_data=f"add_fav_{idx}"),
                InlineKeyboardButton(text="❌ Закончить", callback_data="stop")
            ]
        )
        if message:
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    # Добавляем пагинацию, если результатов больше одной страницы
    if len(pages) > 1:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        if current_page > 0:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="← Предыдущая", callback_data="prev_page")])
        if current_page < len(pages) - 1:
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="Следующая →", callback_data="next_page")])
        if message:
            await message.answer("Для навигации между страницами:", reply_markup=keyboard)
        else:
            await bot.send_message(chat_id, "Для навигации между страницами:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("add_fav_"))
async def add_to_favorites(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    index = int(callback.data.split("_")[2]) - 1
    result = user_data[chat_id]["results"][index]
    user_data[chat_id]["favorites"].append(result)
    await callback.answer("Добавлено в избранное!")


@dp.callback_query(lambda c: c.data == "prev_page")
async def prev_page(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    current_page = user_data[chat_id].get("current_page", 0)
    if current_page > 0:
        user_data[chat_id]["current_page"] -= 1
        await show_results(chat_id, callback.message)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "next_page")
async def next_page(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    current_page = user_data[chat_id].get("current_page", 0)
    pages = [user_data[chat_id]["results"][i:i + 10] for i in range(0, len(user_data[chat_id]["results"]), 10)]
    if current_page < len(pages) - 1:
        user_data[chat_id]["current_page"] += 1
        await show_results(chat_id, callback.message)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "stop")
async def stop_search(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user_data[chat_id]["results"] = []
    user_data[chat_id]["index"] = 0
    await callback.answer("Поиск завершён.")
    await callback.message.answer("Поиск остановлен. Выберите действие:", reply_markup=create_main_menu())


@dp.message(lambda message: message.text == "🏠 Главное меню")
async def return_to_menu(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_data:
        user_data[chat_id]["is_searching"] = False
    await message.answer("Вы вернулись в главное меню.", reply_markup=create_main_menu())


async def run_bot():
    try:
        logger.info("Бот запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка: {e}")


if __name__ == '__main__':
    asyncio.run(run_bot())
