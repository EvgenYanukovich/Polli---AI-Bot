import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, TEMP_DIR, LOG_LEVEL
from database import db
from handlers import commands, thinking_mode, chat_commands
from services.pollinations_api import PollinationsService

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    try:
        # Инициализируем базу данных
        await db.init_db()
        logger.info("Database initialized")
        
        # Создаем сервис AI
        ai_service = PollinationsService()
        logger.info("AI service created")
        
        # Создаем бота и диспетчер с настройками по умолчанию
        default = DefaultBotProperties(parse_mode=ParseMode.HTML)
        bot = Bot(token=BOT_TOKEN, default=default)
        dp = Dispatcher(storage=MemoryStorage())
        logger.info("Bot and dispatcher initialized")
        
        # Регистрируем обработчики
        # Регистрируем базовые команды
        commands.register_handlers(dp, ai_service)
        logger.info("Basic command handlers registered")
        
        # Регистрируем обработчики чатов (до обработчиков режима размышления!)
        chat_commands.register_handlers(dp)
        logger.info("Chat command handlers registered")
        
        # Регистрируем обработчики режима размышления
        thinking_mode.register_handlers(dp, ai_service)
        logger.info("Thinking mode handlers registered")
        
        # Устанавливаем команды бота
        await bot.set_my_commands(commands.get_commands())
        logger.info("Bot commands set")
        
        # Запускаем поллинг
        logger.info("Start polling")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise

    finally:
        await bot.session.close()
        await db.close_db()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
