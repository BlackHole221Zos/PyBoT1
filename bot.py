from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp
from bs4 import BeautifulSoup
import logging
import asyncio
import random
import os
from yt_dlp import YoutubeDL
import subprocess

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = 'ваш_токен'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_data = {}

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
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )

def create_settings_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Установить платформу по умолчанию", callback_data="set_default_platform")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
        ]
    )

def create_platform_choice():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Rutube", callback_data="platform_rutube"),
                InlineKeyboardButton(text="Bandcamp", callback_data="platform_bandcamp")
            ]
        ]
    )

def create_search_buttons():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="← Назад", callback_data="prev"),
                InlineKeyboardButton(text="Далее →", callback_data="next")
            ],
            [
                InlineKeyboardButton(text="⭐ В избранное", callback_data="add_fav"),
                InlineKeyboardButton(text="🎲 Случайный", callback_data="random")
            ],
            [
                InlineKeyboardButton(text="⬇️ Скачать", callback_data="download"),
                InlineKeyboardButton(text="🔄 Новый поиск", callback_data="new"),
                InlineKeyboardButton(text="❌ Закончить", callback_data="stop")
            ]
        ]
    )

# Поиск видео на Rutube
async def find_videos(query: str):
    url = f"https://rutube.ru/api/search/video/?query={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return [(item.get("title", "Без названия"), f"https://rutube.ru/video/{item.get('id')}/") for item in data.get("results", [])]
            logger.error(f"Ошибка запроса: {response.status}")
    return []

# Поиск музыки на Bandcamp
async def find_music(query: str):
    url = f"https://bandcamp.com/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                soup = BeautifulSoup(await response.text(), 'html.parser')
                return [(item.find('div', {'class': 'heading'}).text.strip(), item.find('a')['href']) for item in soup.find_all('li', {'class': 'searchresult'})]
            logger.error(f"Ошибка запроса: {response.status}")
    return []

# Скачивание медиафайла
ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': '%(title)s.%(ext)s',
}

async def download_media(url: str, chat_id: int):
    try:
        # Проверяем размер файла перед скачиванием
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True) as response:
                if response.status != 200:
                    logger.error(f"Не удалось получить информацию о файле: {response.status}")
                    return None
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > 2 * 1024 * 1024 * 1024:  # Проверка на 2 ГБ
                    logger.warning("Файл слишком большой для отправки.")
                    return "too_large"

        # Скачиваем файл, если он подходит по размеру
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            return file_path

    except Exception as e:
        logger.error(f"Ошибка при скачивании: {e}")
        return None

# Функция для перекодирования видео через FFMPEG
async def convert_video(input_file: str, output_file: str):
    try:
        command = [
            "ffmpeg",
            "-i", input_file,
            "-c:v", "libx264",
            "-crf", "23",  # Качество видео (меньше число — лучше качество)
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",  # Битрейт аудио
            "-movflags", "+faststart",
            output_file
        ]
        process = await asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(f"Ошибка при конвертации видео: {stderr.decode()}")
            return None
        return output_file
    except Exception as e:
        logger.error(f"Ошибка при конвертации видео: {e}")
        return None

@dp.message(Command("start"))
async def start_bot(message: types.Message):
    name = message.from_user.first_name
    username = message.from_user.username
    greeting = f"Привет, {name}!" + (f" (@{username})" if username else "")
    await message.answer(greeting)
    await message.answer("Я бот для поиска видео и музыки. Нажми «▶️ Начать», чтобы выбрать тип поиска.", reply_markup=create_start_keyboard())

@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = (
        "📚 Доступные команды:\n\n"
        "▶️ Начать - начать работу с ботом\n"
        "🎥 Видео на Rutube - поиск видео\n"
        "🎵 Музыка на Bandcamp - поиск музыки\n"
        "⭐ Избранное - ваши сохранённые результаты\n"
        "⚙️ Настройки - настройки платформ\n"
        "📜 История - история поисковых запросов\n"
        "❌ Очистить историю - удалить историю запросов\n"
        "ℹ️ Помощь - это сообщение"
    )
    await message.answer(help_text, reply_markup=create_main_menu())

@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def help_button(message: types.Message):
    await help_command(message)

@dp.message(lambda message: message.text == "⚙️ Настройки")
async def settings_menu(message: types.Message):
    await message.answer("Настройки платформ:", reply_markup=create_settings_menu())

@dp.callback_query(lambda c: c.data == "set_default_platform")
async def set_default_platform(callback: types.CallbackQuery):
    await callback.message.edit_text("Выберите платформу по умолчанию:", reply_markup=create_platform_choice())

@dp.callback_query(lambda c: c.data.startswith("platform_"))
async def process_platform_choice(callback: types.CallbackQuery):
    platform = callback.data.split("_")[1]
    user_data[callback.message.chat.id]["settings"]["default_platform"] = platform
    await callback.answer(f"Платформа {platform.capitalize()} установлена по умолчанию!")
    await callback.message.edit_text("Главное меню:", reply_markup=create_main_menu())

@dp.message(lambda message: message.text == "⭐ Избранное")
async def show_favorites(message: types.Message):
    chat_id = message.chat.id
    if not user_data.get(chat_id, {}).get("favorites"):
        await message.answer("В избранном пока ничего нет.")
        return
    builder = InlineKeyboardBuilder()
    for idx, item in enumerate(user_data[chat_id]["favorites"], 1):
        builder.add(InlineKeyboardButton(text=f"⭐ {idx}", callback_data=f"fav_{idx}"))
    builder.adjust(2)
    await message.answer("Ваше избранное:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith("fav_"))
async def show_favorite_item(callback: types.CallbackQuery):
    index = int(callback.data.split("_")[1]) - 1
    item = user_data[callback.message.chat.id]["favorites"][index]
    await callback.message.answer(f"⭐ Избранное:\n{item[0]}\n{item[1]}")

@dp.callback_query(lambda c: c.data == "add_fav")
async def add_to_favorites(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    current = user_data[chat_id]["results"][user_data[chat_id]["index"]]
    user_data[chat_id]["favorites"].append(current)
    await callback.answer("Добавлено в избранное!")

@dp.callback_query(lambda c: c.data == "random")
async def random_result(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user_data[chat_id]["index"] = random.randint(0, len(user_data[chat_id]["results"]) - 1)
    await show_result(chat_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "prev")
async def prev_result(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if user_data[chat_id]["index"] > 0:
        user_data[chat_id]["index"] -= 1
        await show_result(chat_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "next")
async def next_result(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if user_data[chat_id]["index"] < len(user_data[chat_id]["results"]) - 1:
        user_data[chat_id]["index"] += 1
        await show_result(chat_id)
    await callback.answer()

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
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True)
    )

@dp.message(lambda message: message.text == "🏠 Главное меню")
async def return_to_menu(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_data:
        user_data[chat_id]["is_searching"] = False
    await message.answer("Вы вернулись в главное меню.", reply_markup=create_main_menu())

@dp.message(lambda message: message.text == "📜 История")
async def show_history(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_data and user_data[chat_id]["history"]:
        history = "\n".join(f"{i}. {item}" for i, item in enumerate(user_data[chat_id]["history"], 1))
        await message.answer(f"История запросов:\n{history}")
    else:
        await message.answer("История запросов пуста.")

@dp.message(lambda message: message.text == "❌ Очистить историю")
async def clear_history(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_data:
        user_data[chat_id]["history"] = []
        await message.answer("История запросов очищена.", reply_markup=create_main_menu())
    else:
        await message.answer("История запросов уже пуста.", reply_markup=create_main_menu())

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
    else:
        results = await find_music(query)
    if not results:
        await message.answer("Ничего не найдено. Попробуй другой запрос.", reply_markup=create_main_menu())
        return
    user_data[chat_id]["results"] = results
    user_data[chat_id]["index"] = 0
    await show_result(chat_id, message)

async def show_result(chat_id: int, message: types.Message = None):
    result = user_data[chat_id]["results"][user_data[chat_id]["index"]]
    text = f"🔍 Результат {user_data[chat_id]['index']+1}/{len(user_data[chat_id]['results'])}\n"
    text += f"📌 Название: {result[0]}\n🔗 Ссылка: {result[1]}"
    if message:
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=create_search_buttons())
    else:
        await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=create_search_buttons())

@dp.callback_query(lambda c: c.data == "new")
async def new_search(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user_data[chat_id]["results"] = []
    user_data[chat_id]["index"] = 0
    await callback.answer("Начни новый поиск.")
    await callback.message.answer("Введи новый запрос:", reply_markup=create_main_menu())

@dp.callback_query(lambda c: c.data == "stop")
async def stop_search(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user_data[chat_id]["results"] = []
    user_data[chat_id]["index"] = 0
    await callback.answer("Поиск завершён.")
    await callback.message.answer("Поиск остановлен. Выберите действие:", reply_markup=create_main_menu())

@dp.callback_query(lambda c: c.data == "download")
async def download_file(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in user_data or "results" not in user_data[chat_id] or "index" not in user_data[chat_id]:
        await callback.answer("Нет доступных результатов для скачивания.")
        return
    try:
        url = user_data[chat_id]["results"][user_data[chat_id]["index"]][1]
    except IndexError:
        await callback.answer("Выбранный результат недоступен для скачивания.")
        return

    loading_message = await callback.message.answer("⏳ Загрузка файла...")
    file_result = await download_media(url, chat_id)

    if file_result == "too_large":
        await loading_message.edit_text("❌ Файл слишком большой для отправки (максимум 2 ГБ).")
    elif file_result:
        try:
            file_size = os.path.getsize(file_result)
            if file_size > 2 * 1024 * 1024 * 1024:  # Проверка на 2 ГБ
                await loading_message.edit_text("❌ Файл слишком большой для отправки (максимум 2 ГБ).")
                return

            # Если это видео, попробуем его перекодировать через FFMPEG
            if file_result.endswith('.mp4'):
                converted_file = await convert_video(file_result, f"{file_result}.converted.mp4")
                if converted_file:
                    file_result = converted_file

            if file_result.endswith('.mp4'):  # Если это видео
                video = FSInputFile(file_result)
                await bot.send_video(chat_id, video=video, caption="Загруженное видео")
            elif file_result.endswith('.mp3'):  # Если это аудио
                audio = FSInputFile(file_result)
                await bot.send_audio(chat_id, audio=audio, caption="Загруженный аудиофайл")
            else:
                document = FSInputFile(file_result)
                await bot.send_document(chat_id, document=document, caption="Загруженный файл")
        except Exception as e:
            logger.error(f"Ошибка при отправке файла: {e}")
            await callback.message.answer(f"Произошла ошибка: {str(e)}")
        finally:
            if os.path.exists(file_result):
                os.remove(file_result)  # Удаляем исходный файл
            if os.path.exists(f"{file_result}.converted.mp4"):
                os.remove(f"{file_result}.converted.mp4")  # Удаляем преобразованный файл
    else:
        await loading_message.edit_text("❌ Не удалось скачать файл.")
    await callback.message.edit_reply_markup(reply_markup=None)

async def run_bot():
    try:
        logger.info("Бот запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка: {e}")

if __name__ == '__main__':
    asyncio.run(run_bot())
