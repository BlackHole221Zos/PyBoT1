# 🎥🎵 [techbotMedia](https://t.me/technicBotMedia)

**techbotMedia** — это ваш помощник для поиска и скачивания медиаконтента. Бот поддерживает поиск видео на **Rutube** и музыки на **Bandcamp** с возможностью сохранения избранного, управления историей запросов и прямого скачивания файлов.

---

## ✨ Возможности бота:

- 🎥 **Поиск видео на Rutube**
- 🎵 **Поиск музыки на Bandcamp**
- ⭐ **Сохранение избранных результатов**
- 📜 **Просмотр истории запросов**
- ⚙️ **Настройка платформы по умолчанию**
- ⬇️ **Скачивание найденных файлов**
- 💰 **Донат для поддержки проекта** ❤️

---

## Как использовать бота? 🧩

### Базовые команды:

- **/start** — Начать работу с ботом 🌟

### Главное меню:

1. 🎥 **Видео на Rutube** — Искать видео
2. 🎵 **Музыка на Bandcamp** — Искать музыку
3. ⭐ **Избранное** — Просмотреть сохраненные результаты
4. ⚙️ **Настройки** — Изменить параметры бота
5. 📜 **История** — Посмотреть историю запросов
6. ❌ **Очистить историю** — Удалить все сохраненные запросы
7. ℹ️ **Помощь** — Получить информацию о боте
8. 💰 **Донат** — Поддержать проект ❤️

---

### Поиск контента 🔍
1. Выберите тип контента (видео или музыка) 🎬🎵
2. Введите ваш запрос 🔍
3. Переключайтесь между результатами с помощью кнопок "← Назад" и "Далее →" ⏪➡️
4. Добавляйте понравившиеся результаты в избранное ⭐
5. Скачивайте выбранные файлы ⬇️

---

## Техническая информация 💻

### Что используется в проекте?

- **Python 3.8+** — Язык программирования 🐍
- **aiogram** — Для работы с Telegram API 🤖
- **aiohttp** — Для выполнения HTTP-запросов 🌐
- **BeautifulSoup** — Для парсинга HTML страниц 📄
- **yt-dlp** — Для скачивания медиаконтента 📥

---

## Как установить бота локально? 🔧

### 1. Получите токен для бота
Для того чтобы запустить бота, вам нужен уникальный токен от Telegram. Для этого:
1. Перейдите в [BotFather](https://core.telegram.org/bots#botfather).
2. Создайте нового бота, используя команду `/newbot`.
3. Скопируйте токен, который будет выдан в процессе.

### 2. Установите зависимости

Убедитесь, что у вас установлен **Python 3.8** или выше. Затем выполните следующие шаги для установки зависимостей:

1) Установите **aiogram**:
    ```bash
    pip install aiogram
    ```

2) Установите **aiohttp**:
    ```bash
    pip install aiohttp
    ```

3) Установите **beautifulsoup4**:
    ```bash
    pip install beautifulsoup4
    ```

4) Установите **yt-dlp**:
    ```bash
    pip install yt-dlp
    ```

### 3. Вставьте токен в код

Откройте файл `bot.py` и найдите строку с токеном:

```python
BOT_TOKEN = 'YOUR_BOT_TOKEN'
```

Замените `'YOUR_BOT_TOKEN'` на ваш реальный токен, который вы получили от **BotFather**.

### 4. Запустите бота

Теперь можно запустить бота:

```bash
python bot.py
```

После этого бот будет готов к работе, и вы сможете взаимодействовать с ним через Telegram.

---

## Структура проекта
```bash
PyMediaBot/
├── bot.py               Основной код бота
├── README.md            Документация
└── requirements.txt     Список зависимостей
```

---

## Пример использования 🎯

1. Нажмите **/start**, чтобы начать работу 🚀
2. Выберите тип контента (видео/музыка) 🎬🎵
3. Введите ваш запрос 🔍
4. Переключайтесь между результатами с помощью кнопок ⏪➡️
5. Скачивайте или добавляйте в избранное нужные файлы ⬇️⭐

---

## Лицензия 📜

Этот проект распространяется по лицензии MIT. Подробности можно найти в [LICENSE.md](LICENSE.md).

---

## Поддержка проекта 💰

Если вам понравился бот и вы хотите его поддержать, вы можете сделать донат! Это поможет нам развивать проект дальше. Ваша поддержка очень важна для нас! ❤️

[Донат](https://www.donationalerts.com/r/black_h0le_d)
