import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message

# токены
BOT_TOKEN = '7141735821:AAFDkmNQByppo_g05PvQcihwrmKVVGX0ajg'
GOOGLE_API_KEY = 'AIzaSyABP6N_DVSI8CnvWDCJZVRZswY3Idn-R-E'
GOOGLE_SEARCH_ENGINE_ID = 'b205be29cb0a345ce'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()





# Словарь для хранения истории запросов и текущего индекса изображения
user_data = {}

async def fetch_google_images(query: str, start_index: int = 1):
    """Функция для поиска изображений через Google Custom Search API."""
    url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_SEARCH_ENGINE_ID,
        "searchType": "image",
        "start": start_index  # параметр для пагинации
    }






    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if 'items' in data:
                    return [item['link'] for item in data['items']]  # возвращаем список URL изображений
            return None

@dp.message()
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # логируем входящее сообщение
    print(f"User {user_id} sent: {message.text}")

    if message.text.lower() == 'привет':
        await message.answer('Привет! Как дела?')
    elif message.text.lower() == 'пока':
        await message.answer('Пока! Хорошего дня!')
    elif message.text.lower() == 'факт':
        facts = [
            "Земля - третья планета от Солнца.",
            "Венера - самая горячая планета в Солнечной системе.",
            "У Юпитера больше всего спутников."
        ]
        fact = facts[hash(user_id) % len(facts)]
        await message.answer(f"Вот интересный факт: {fact}")
    elif message.text.lower() == 'давай другое':
        # проверяем, есть ли сохраненный запрос для пользователя
        if user_id in user_data:
            query = user_data[user_id]['query']
            current_index = user_data[user_id]['index']
            images = user_data[user_id]['images']







            # логируем текущее состояние
            print(f"User {user_id} data: query='{query}', index={current_index}, images_found={len(images)}")

            if current_index < len(images):
                # отправляем следующее изображение
                image_url = images[current_index]
                await message.answer_photo(image_url, caption=f"Вот другое изображение по запросу: {query}")
                # обновляем индекс
                user_data[user_id]['index'] += 1
            else:
                # если изображения закончились, ищем новые
                new_images = await fetch_google_images(query, start_index=current_index + 1)
                if new_images:
                    user_data[user_id]['images'].extend(new_images)
                    image_url = new_images[0]
                    await message.answer_photo(image_url, caption=f"Вот другое изображение по запросу: {query}")
                    user_data[user_id]['index'] += 1
                else:
                    await message.answer("Больше изображений по этому запросу нет.")
        else:
            # Логируем, что данных нет
            print(f"User {user_id} has no saved data.")
            await message.answer("Сначала напишите запрос, например: 'Фото Лес'.")
    else:
        # Новый запрос на фото
        query = message.text
        images = await fetch_google_images(query)
        if images:
            # Сохраняем запрос и изображения для пользователя
            user_data[user_id] = {
                'query': query,
                'images': images,
                'index': 1  # Начинаем с первого изображения
            }
            # Логируем сохраненные данные
            print(f"User {user_id} saved data: query='{query}', images_found={len(images)}")
            # Отправляем первое изображение
            await message.answer_photo(images[0], caption=f"Вот изображение по запросу: {query}")
        else:
            # Логируем, что изображения не найдены
            print(f"User {user_id} requested '{query}', but no images were found.")
            await message.answer("Не удалось найти изображение. Попробуйте другой запрос.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())


    # Нк забыть добавить логику по давай другое
    # БОТ НЕ КОРРЕКТНО РОАБОТАЕТ
    