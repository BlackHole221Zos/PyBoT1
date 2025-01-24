Многофункциональный Telegram Бот
Этот Telegram бот — универсальный помощник, который сочетает в себе множество функций: от простого общения до поиска изображений через Google Custom Search API. Бот легко адаптируется под нужды пользователя и предоставляет удобный интерфейс для взаимодействия.

Основные функции бота
1. Общение
Привет: Бот отвечает приветствием.

Пока: Бот прощается с пользователем.

2. Интересные факты
Факт: Бот отправляет случайный факт о планетах.

3. Поиск изображений
Запрос на изображение: Пользователь может ввести любой текстовый запрос (например, "Фото Лес"), и бот отправит изображение, соответствующее этому запросу.

Давай другое: Если пользователь уже делал запрос на изображение, бот отправит следующее изображение из результатов поиска.

4. Расширенные возможности
Пагинация: Бот поддерживает пагинацию, позволяя пользователю запрашивать дополнительные изображения по тому же запросу.

История запросов: Бот сохраняет историю запросов и текущий индекс изображения для каждого пользователя, чтобы обеспечить корректную работу команды "давай другое".

Как использовать бота
Основные команды:
Привет: Начните общение с ботом, отправив "Привет".

Пока: Завершите общение, отправив "Пока".

Факт: Получите случайный факт, отправив "Факт".

Поиск изображений: Введите любой запрос (например, "Фото Лес"), и бот отправит вам изображение.

Дополнительные изображения: Используйте команду "давай другое", чтобы получить следующее изображение по тому же запросу.

Установка и запуск
Требования:
Python 3.7 или выше

Установленные библиотеки: aiogram, aiohttp

Установка:
Клонируйте репозиторий:

bash
Copy
git clone https://github.com/yourusername/telegram-multifunctional-bot.git
cd telegram-multifunctional-bot
Установите необходимые зависимости:

bash
Copy
pip install -r requirements.txt
Создайте файл .env и добавьте туда ваши токены:

plaintext
Copy
BOT_TOKEN=ваш_токен_бота
GOOGLE_API_KEY=ваш_google_api_ключ
GOOGLE_SEARCH_ENGINE_ID=ваш_идентификатор_поисковой_системы
Запустите бота:

bash
Copy
python bot.py
Логирование
Бот логирует все входящие сообщения и действия пользователя в консоль, что помогает отслеживать его работу и находить возможные ошибки.

Зависимости
aiogram: Библиотека для работы с Telegram Bot API.

aiohttp: Библиотека для асинхронных HTTP-запросов.

Лицензия
Этот проект распространяется под лицензией MIT. См. файл LICENSE для получения дополнительной информации.

Пример взаимодействия с ботом
Запуск бота: После запуска бота, вы можете начать с ним взаимодействовать в Telegram.

Приветствие: Напишите "Привет", и бот ответит вам.

Поиск изображений: Введите любой запрос, например, "Фото Лес", и бот отправит вам соответствующее изображение.

Дополнительные изображения: Используйте команду "давай другое", чтобы получить следующее изображение по тому же запросу.

Факты: Напишите "Факт", и бот отправит вам случайный факт о планетах.

Прощание: Напишите "Пока", и бот попрощается с вами.

Примечание: Убедитесь, что вы заменили ваш_токен_бота, ваш_google_api_ключ и ваш_идентификатор_поисковой_системы на реальные значения перед запуском бота.
