from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp
from bs4 import BeautifulSoup
import logging
import asyncio
import os
from yt_dlp import YoutubeDL
from pathlib import Path
import tempfile
import shutil

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = 'ваш_токен'
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_data = {}
active_downloads = {}
DONATE_URL = "https://www.donationalerts.com/r/black_h0le_d"
RUTUBE_DOWNLOAD_SITE = "https://cobalt.tools/?url="

def save_user_query(chat_id: int, query: str):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "history": [],
            "results": [],
            "index": 0,
            "type": None,
            "settings": {"default_platform": None, "results_per_page": 10},
            "is_searching": False,
            "favorites": []
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
            [KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="❌ Очистить историю")],
            [KeyboardButton(text="⭐ Избранное"), KeyboardButton(text="ℹ️ Помощь")],
            [KeyboardButton(text="💰 Донат")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start_bot(message: types.Message):
    name = message.from_user.first_name
    username = message.from_user.username
    greeting = f"Привет, {name}!" + (f" (@{username})" if username else "")
    await message.answer(greeting)
    await message.answer(
        "Я бот для поиска видео и музыки. Нажми «▶️ Начать», чтобы выбрать тип поиска.",
        reply_markup=create_start_keyboard()
    )

@dp.message(lambda message: message.text == "💰 Донат")
async def donate_handler(message: types.Message):
    await message.answer(
        "Спасибо за поддержку! Вы можете сделать донат по ссылке ниже:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❤️ Перейти к донату", url=DONATE_URL)]]
        )
    )

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
            "settings": {"default_platform": None, "results_per_page": 10},
            "is_searching": True,
            "favorites": []
        }
    else:
        user_data[chat_id]["is_searching"] = True
    user_data[chat_id]["type"] = "video" if message.text == "🎥 Видео на Rutube" else "music"
    await message.answer(
        f"Отлично! Теперь я буду искать {'видео на Rutube' if user_data[chat_id]['type'] == 'video' else 'музыку на Bandcamp'}. Введи запрос:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True)
    )

@dp.message()
async def process_query(message: types.Message):
    chat_id = message.chat.id
    query = message.text.strip()

    if query in [
        "🎥 Видео на Rutube", "🎵 Музыка на Bandcamp", "⚙️ Настройки",
        "📜 История", "❌ Очистить историю", "ℹ️ Помощь", "💰 Донат", "🏠 Главное меню", "⭐ Избранное"
    ]:
        await handle_menu_commands(message)
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
    user_data[chat_id]["index"] = 0
    await show_results(chat_id, message)

async def handle_menu_commands(message: types.Message):
    query = message.text.strip()
    if query == "⚙️ Настройки":
        await settings_handler(message)
    elif query == "📜 История":
        await show_history(message)
    elif query == "❌ Очистить историю":
        await clear_history(message)
    elif query == "ℹ️ Помощь":
        await help_handler(message)
    elif query == "⭐ Избранное":
        await show_favorites(message)
    elif query == "💰 Донат":
        await donate_handler(message)
    elif query == "🏠 Главное меню":
        await return_to_menu(message)

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

async def show_results(chat_id: int, message: types.Message = None):
    results = user_data[chat_id]["results"]
    if not results:
        await bot.send_message(chat_id, "Ничего не найдено.")
        return

    max_results_to_show = user_data[chat_id]["settings"]["results_per_page"]
    total_results = len(results)
    pages = [results[i:i + max_results_to_show] for i in range(0, total_results, max_results_to_show)]
    current_page = user_data[chat_id].get("current_page", 0)
    user_data[chat_id]["current_page"] = current_page

    for idx, result in enumerate(pages[current_page], start=current_page * max_results_to_show + 1):
        text = f"🔍 Результат {idx}/{total_results}\n"
        text += f"📌 Название: {result[0]}\n🔗 Ссылка: {result[1]}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])

        is_favorite = any(fav[1] == result[1] for fav in user_data[chat_id]["favorites"])
        favorite_button_text = "⭐ Удалить из избранного" if is_favorite else "⭐ Добавить в избранное"
        favorite_callback_data = f"remove_favorite_{idx - 1}" if is_favorite else f"add_favorite_{idx - 1}"

        if user_data[chat_id]["type"] == "video":
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="⬇️ Скачать видео", callback_data=f"copy_link_{idx - 1}")
            ])
        elif user_data[chat_id]["type"] == "music":
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬇️ Скачать", callback_data=f"download_{idx - 1}")])

        keyboard.inline_keyboard.append([InlineKeyboardButton(text=favorite_button_text, callback_data=favorite_callback_data)])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="❌ Закончить", callback_data="stop")])

        if message:
            await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

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

@dp.callback_query(lambda c: c.data.startswith("copy_link_"))
async def copy_download_link(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        index = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка: Неверный формат данных.")
        return

    if chat_id not in user_data or "results" not in user_data[chat_id]:
        await callback.answer("Нет доступных результатов.")
        return

    results = user_data[chat_id]["results"]
    if index < 0 or index >= len(results):
        await callback.answer("Выбранный результат недоступен.")
        return

    result = results[index]
    video_link = result[1]  # Оригинальная ссылка на видео
    cobalt_url = f"{RUTUBE_DOWNLOAD_SITE}{video_link}"  # Ссылка для Cobalt.tools

    # Отправляем сообщение с двумя кнопками
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Копировать ссылку на видео", callback_data=f"copy_video_link_{index}")],
            [InlineKeyboardButton(text="📥 Перейти на Cobalt.tools", url=cobalt_url)]
        ])
    )
    await callback.answer("Готово!")

@dp.callback_query(lambda c: c.data.startswith("copy_video_link_"))
async def copy_video_link(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        index = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("Ошибка: Неверный формат данных.")
        return

    if chat_id not in user_data or "results" not in user_data[chat_id]:
        await callback.answer("Нет доступных результатов.")
        return

    results = user_data[chat_id]["results"]
    if index < 0 or index >= len(results):
        await callback.answer("Выбранный результат недоступен.")
        return

    result = results[index]
    video_link = result[1]  # Оригинальная ссылка на видео

    # Отправляем оригинальную ссылку для копирования
    await callback.message.answer(
        f"Скопируйте эту ссылку на видео:\n```\n{video_link}\n```",
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer("Теперь выделите и скопируйте ссылку!")

@dp.callback_query(lambda c: c.data.startswith("add_favorite_"))
async def add_to_favorites(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        index = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка: Неверный формат данных.")
        return

    if chat_id not in user_data or "results" not in user_data[chat_id]:
        await callback.answer("Нет доступных результатов для добавления в избранное.")
        return

    results = user_data[chat_id]["results"]
    if index < 0 or index >= len(results):
        await callback.answer("Выбранный результат недоступен.")
        return

    result = results[index]
    if not any(fav[1] == result[1] for fav in user_data[chat_id]["favorites"]):
        user_data[chat_id]["favorites"].append(result)
        await callback.answer("Добавлено в избранное!")
    else:
        await callback.answer("Уже в избранном.")
    await update_keyboard_after_favorite_action(callback, index)

@dp.callback_query(lambda c: c.data.startswith("remove_favorite_"))
async def remove_from_favorites(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        index = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка: Неверный формат данных.")
        return

    if chat_id not in user_data or "results" not in user_data[chat_id]:
        await callback.answer("Нет доступных результатов для удаления из избранного.")
        return

    results = user_data[chat_id]["results"]
    if index < 0 or index >= len(results):
        await callback.answer("Выбранный результат недоступен.")
        return

    result = results[index]
    user_data[chat_id]["favorites"] = [fav for fav in user_data[chat_id]["favorites"] if fav[1] != result[1]]
    await callback.answer("Удалено из избранного!")
    await update_keyboard_after_favorite_action(callback, index)

async def update_keyboard_after_favorite_action(callback: types.CallbackQuery, index: int):
    chat_id = callback.message.chat.id
    results = user_data[chat_id]["results"]
    result = results[index]

    text = f"🔍 Результат {index + 1}/{len(results)}\n"
    text += f"📌 Название: {result[0]}\n🔗 Ссылка: {result[1]}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    is_favorite = any(fav[1] == result[1] for fav in user_data[chat_id]["favorites"])
    favorite_button_text = "⭐ Удалить из избранного" if is_favorite else "⭐ Добавить в избранное"
    favorite_callback_data = f"remove_favorite_{index}" if is_favorite else f"add_favorite_{index}"

    if user_data[chat_id]["type"] == "video":
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="⬇️ Скачать видео", callback_data=f"copy_link_{index}")
        ])
    elif user_data[chat_id]["type"] == "music":
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬇️ Скачать", callback_data=f"download_{index}")])

    keyboard.inline_keyboard.append([InlineKeyboardButton(text=favorite_button_text, callback_data=favorite_callback_data)])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="❌ Закончить", callback_data="stop")])

    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

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
    pages = [user_data[chat_id]["results"][i:i + user_data[chat_id]["settings"]["results_per_page"]] for i in range(0, len(user_data[chat_id]["results"]), user_data[chat_id]["settings"]["results_per_page"])]
    if current_page < len(pages) - 1:
        user_data[chat_id]["current_page"] += 1
        await show_results(chat_id, callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("download_"))
async def download_file(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        index = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка: Неверный формат данных.")
        return

    if chat_id not in user_data or "results" not in user_data[chat_id]:
        await callback.answer("Нет доступных результатов для скачивания.")
        return

    results = user_data[chat_id]["results"]
    if index < 0 or index >= len(results):
        await callback.answer("Выбранный результат недоступен для скачивания.")
        return

    result = results[index]
    url = result[1]
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить загрузку", callback_data=f"cancel_download_{chat_id}")]
    ])
    
    loading_message = await callback.message.answer(
        "⏳ Загрузка файла началась...",
        reply_markup=cancel_keyboard
    )
    
    temp_dir = tempfile.mkdtemp()
    
    download_task = asyncio.create_task(
        asyncio.to_thread(download_media, url, chat_id, temp_dir)
    )
    active_downloads[chat_id] = {
        "task": download_task,
        "message_id": loading_message.message_id,
        "cancelled": False,
        "temp_dir": temp_dir
    }
    
    try:
        file_paths = await download_task
        if active_downloads.get(chat_id, {}).get("cancelled", False):
            return
            
        if not file_paths:
            await bot.edit_message_text(
                "❌ Не удалось скачать файл.",
                chat_id=chat_id,
                message_id=loading_message.message_id
            )
            return

        for file_path in file_paths:
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:
                document = FSInputFile(file_path)
                await bot.send_document(chat_id, document=document, caption="Файл слишком большой для отправки как медиа, отправляю как документ.")
            else:
                if file_path.endswith('.mp3'):
                    audio = FSInputFile(file_path)
                    await bot.send_audio(chat_id, audio=audio, caption="Загруженный аудиофайл")
                else:
                    document = FSInputFile(file_path)
                    await bot.send_document(chat_id, document=document, caption="Загруженный файл")
            await asyncio.sleep(1)
            
        await bot.edit_message_text(
            "✅ Все файлы успешно загружены!",
            chat_id=chat_id,
            message_id=loading_message.message_id,
            reply_markup=None
        )
    except asyncio.CancelledError:
        logger.info(f"Download task cancelled for chat_id {chat_id}")
        return
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        await callback.message.answer(f"Произошла ошибка: {str(e)}")
    finally:
        if chat_id in active_downloads:
            try:
                shutil.rmtree(active_downloads[chat_id]["temp_dir"])
            except:
                pass
            del active_downloads[chat_id]
        else:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    await callback.message.edit_reply_markup(reply_markup=None)

@dp.callback_query(lambda c: c.data.startswith("cancel_download_"))
async def cancel_download(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id in active_downloads:
        active_downloads[chat_id]["cancelled"] = True
        active_downloads[chat_id]["task"].cancel()
        
        await bot.edit_message_text(
            "❌ Загрузка отменена",
            chat_id=chat_id,
            message_id=active_downloads[chat_id]["message_id"],
            reply_markup=None
        )
        
        await bot.send_message(
            chat_id,
            "Вы вернулись в главное меню.",
            reply_markup=create_main_menu()
        )
        
        try:
            shutil.rmtree(active_downloads[chat_id]["temp_dir"])
        except Exception as e:
            logger.error(f"Ошибка при удалении временной директории: {e}")
            
        del active_downloads[chat_id]
    else:
        await callback.answer("Нет активной загрузки для отмены")
    await callback.answer()

def download_media(url: str, chat_id: int, temp_dir: str, ydl_opts: dict = None):
    try:
        if ydl_opts is None:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [lambda d: check_cancel(d, chat_id)],
                'noplaylist': True,
            }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
            return downloaded_files
    except Exception as e:
        if str(e) == "Download cancelled":
            logger.info(f"Download cancelled for chat_id {chat_id}")
            return None
        logger.error(f"Ошибка при скачивании: {e}")
        return []

def check_cancel(d, chat_id):
    if chat_id in active_downloads and active_downloads[chat_id]["cancelled"]:
        raise Exception("Download cancelled")

@dp.callback_query(lambda c: c.data == "stop")
async def stop_search(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    user_data[chat_id]["results"] = []
    user_data[chat_id]["index"] = 0
    await callback.answer("Поиск завершён.")
    await callback.message.answer("Поиск остановлен. Выберите действие:", reply_markup=create_main_menu())

@dp.message(lambda message: message.text == "⚙️ Настройки")
async def settings_handler(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {
            "history": [],
            "results": [],
            "index": 0,
            "type": None,
            "settings": {"default_platform": None, "results_per_page": 10},
            "is_searching": False,
            "favorites": []
        }
    current_results_per_page = user_data[chat_id]["settings"]["results_per_page"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 результатов", callback_data="set_results_5")],
        [InlineKeyboardButton(text="10 результатов", callback_data="set_results_10")],
        [InlineKeyboardButton(text="20 результатов", callback_data="set_results_20")]
    ])
    await message.answer(
        f"Текущее количество результатов на странице: {current_results_per_page}\n"
        "Выберите новое значение:",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("set_results_"))
async def set_results_per_page(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    results_per_page = int(callback.data.split("_")[-1])
    user_data[chat_id]["settings"]["results_per_page"] = results_per_page
    await callback.answer(f"Установлено {results_per_page} результатов на странице.")
    await callback.message.edit_text("Настройки обновлены.", reply_markup=None)

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

@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def help_handler(message: types.Message):
    help_text = (
        "Это бот для поиска видео и музыки.\n\n"
        "Доступные команды:\n"
        "▶️ Начать - начать новый поиск\n"
        "🎥 Видео на Rutube - поиск видео на Rutube\n"
        "🎵 Музыка на Bandcamp - поиск музыки на Bandcamp\n"
        "⚙️ Настройки - изменить настройки бота\n"
        "📜 История - показать историю запросов\n"
        "❌ Очистить историю - очистить историю запросов\n"
        "⭐ Избранное - показать избранные элементы\n"
        "ℹ️ Помощь - показать это сообщение\n"
        "💰 Донат - поддержать разработчика"
    )
    await message.answer(help_text)

@dp.message(lambda message: message.text == "⭐ Избранное")
async def show_favorites(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {
            "history": [],
            "results": [],
            "index": 0,
            "type": None,
            "settings": {"default_platform": None, "results_per_page": 10},
            "is_searching": False,
            "favorites": []
        }

    favorites = user_data[chat_id]["favorites"]
    if not favorites:
        await message.answer("Ваш список избранных пуст.")
        return

    for idx, fav in enumerate(favorites, start=1):
        text = f"⭐ Избранный элемент {idx}\n"
        text += f"📌 Название: {fav[0]}\n🔗 Ссылка: {fav[1]}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить из избранного", callback_data=f"remove_favorite_{idx - 1}")]
        ])
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def run_bot():
    try:
        logger.info("Бот запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка: {e}")

if __name__ == '__main__':
    asyncio.run(run_bot())
