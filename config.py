import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot токен
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in environment variables")

# Настройки базы данных
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bot.db")

# Временная директория для файлов
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Настройки AI
DEFAULT_TEXT_MODEL = "gpt-4"  # Модель по умолчанию для текстовых запросов
DEFAULT_SYSTEM_PROMPT = """Ты - умный и полезный ассистент. 
Ты всегда стараешься помочь пользователю и ответить на его вопросы максимально точно и полно.
При этом ты остаёшься дружелюбным и вежливым."""

# Максимальное количество сообщений в истории
MAX_HISTORY_LENGTH = 10

# Настройки режима размышления
THINKING_MODE_PROMPT = """Теперь ты должен тщательно обдумывать каждый ответ.
Разбивай свои мысли на короткие сообщения, показывая процесс размышления.
Используй эмодзи для обозначения этапов:
🤔 - начало размышления
💭 - процесс анализа
💡 - появление идеи
✨ - формулировка ответа"""
