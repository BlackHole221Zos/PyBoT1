import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message



# токены 
BOT_TOKEN = '7141735821:AAFDkmNQByppo_g05PvQcihwrmKVVGX0ajg'
# для фото
GOOGLE_API_KEY = 'AIzaSyABP6N_DVSI8CnvWDCJZVRZswY3Idn-R-E'
GOOGLE_SEARCH_ENGINE_ID = 'b205be29cb0a345ce'



bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def fetch_google_image(query: str):
    """Функция для поиска изображений через Google Custom Search API."""
    url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_SEARCH_ENGINE_ID,
        "searchType": "image"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if 'items' in data:
                    return data['items'][0]['link']  # Возвращаем URL первого изображения
            return None

@dp.message()
async def cmd_start(message: Message):
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
        fact = facts[hash(message.from_user.id) % len(facts)]
        await message.answer(f"Вот интересный факт: {fact}")
    else:
        # фото
        query = message.text
        image_url = await fetch_google_image(query)
        if image_url:
            await message.answer_photo(image_url, caption=f"Вот изображение по запросу: {query}")
        else:
            await message.answer("Не удалось найти изображение. Попробуйте другой запрос.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())